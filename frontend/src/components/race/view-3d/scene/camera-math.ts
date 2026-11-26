/**
 * Matemática das câmeras de perseguição e a bordo.
 *
 * Portado de `viz3d/src/cameras/rig.ts`. Duas mudanças, ambas porque aqui a
 * fonte é sempre a corrida ao vivo, posicionada pela pose:
 *
 * - o rig semeia com velocidade zero (carros parados no grid antes da largada);
 *   o viz3d ignorava `speedMps <= 0` para não semear com um readout zerado, e
 *   aqui isso é sinalizado por `carIndex < 0`;
 * - `cut` em `FollowState` substitui o `cutKey` do viz3d: quem escreve a pose
 *   incrementa ao detectar uma descontinuidade (ressincronização), e o rig
 *   corta em vez de amortecer.
 *
 * A perseguição com pose fica atrás do carro, na direção dele suavizada
 * (`yaw`, amortecida com constante `yawTauS`), sem olhar a pista nem o
 * `progress_m`: mirar por pontos da pista (como o viz3d) punha a mira a mais de
 * 8° do carro nas curvas, e a direção da câmera passava a seguir as cordas da
 * polilinha servida, que nas pistas do OpenF1 dobra a cada 14-42 m. O caminho
 * pela pista ficou só para o carro sem pose (e, em desenvolvimento, para
 * comparar: `chaseRig("track")` no gancho).
 *
 * Todo comprimento de arco aqui é *desembrulhado* (cresce sem limite, como
 * `progress_m`); só `toWorld` embrulha, então a linha de chegada não é um caso
 * especial.
 */
import { MathUtils, Vector3 } from "three"

import { curvatureAt, toWorld } from "./track-frame.ts"
import type { TrackFrame } from "./track-frame.ts"

const WORLD_UP = new Vector3(0, 1, 0)
const G = 9.80665
/** Limite de um passo, segundos: uma aba oculta devolve um `delta` enorme. */
export const MAX_DELTA_S = 0.1

export type CameraMode = "orbit" | "chase" | "onboard"

/**
 * Perseguição atrás do carro, pela direção dele ("heading", o padrão) ou o
 * rig antigo, pela pista ("track"), só para comparar no gancho de desenvolvimento.
 */
export type ChaseRig = "heading" | "track"

let chaseRig: ChaseRig = "heading"
export const chaseRigMode = (): ChaseRig => chaseRig
export function setChaseRigMode(next: ChaseRig): void {
  chaseRig = next
}

/** Estado do carro seguido, escrito a cada quadro por `Cars`. */
export interface FollowState {
  /** Comprimento de arco desembrulhado: `progress_m` quando o backend envia. */
  sUnwrapped: number
  d: number
  speedMps: number
  /** Índice do carro; -1 enquanto não há pose. */
  carIndex: number
  /** Pose desenhada do carro (Three.js). Sempre verdadeira na corrida ao vivo. */
  posed: boolean
  x: number
  z: number
  yawRad: number
  /** Incrementado a cada descontinuidade; o rig corta em vez de amortecer. */
  cut: number
  /**
   * Instante de parede do quadro em que a pose foi desenhada, ms (o mesmo
   * carimbo do relógio da reprodução); NaN sem pose.
   */
  wallMs: number
  /** Vista congelada (gancho de desenvolvimento): `wallMs` parado. */
  frozen: boolean
}

export interface RigState {
  /** Comprimento de arco da própria câmera de perseguição; atrasa `trailM`. */
  u: number
  roll: number
  /** Direção suavizada do carro (mesma convenção de `FollowState.yawRad`). */
  yaw: number
  /** Carro para o qual `u`, `roll` e `yaw` foram calculados; -1 = sem semente. */
  carIndex: number
  cut: number
}

export interface CameraPose {
  position: Vector3
  target: Vector3
  up: Vector3
  /** Ponto no chão seguido pela câmera: o carro. */
  anchor: Vector3
}

export interface ChaseConfig {
  trailM: number
  heightM: number
  lookaheadM: number
  targetHeightM: number
  tauS: number
  /** Constante de tempo da direção suavizada do carro, s. */
  yawTauS: number
  fovDeg: number
  /**
   * Só no caminho pela pista (carro sem pose, ou `chaseRig("track")`): quanto
   * a direção da câmera pode se afastar do carro na horizontal. Num
   * grampo, mirar `lookaheadM` à frente pela pista poria o carro na borda da
   * tela (~29° fora do eixo num raio de 25 m); com o limite ele fica perto do
   * centro e a câmera ainda gira para dentro da curva.
   */
  maxOffAxisRad: number
}

export interface OnboardConfig {
  fwdM: number
  heightM: number
  lookaheadM: number
  targetHeightM: number
  rollTauS: number
  maxRollRad: number
  refLatAccelMps2: number
  curvatureSpanM: number
  fovDeg: number
}

/** Atrás e acima, mirando 25 m à frente (`lookaheadM` >> `heightM`, longe da vertical). */
export const CHASE: ChaseConfig = {
  trailM: 9,
  heightM: 3.2,
  lookaheadM: 25,
  targetHeightM: 0.8,
  tauS: 0.3,
  yawTauS: 0.25,
  fovDeg: 45,
  maxOffAxisRad: MathUtils.degToRad(8),
}

/** T-cam: acima e logo atrás do centro do carro, olhando ao longo dele. */
export const ONBOARD: OnboardConfig = {
  fwdM: -2.6,
  heightM: 2.1,
  lookaheadM: 30,
  targetHeightM: 0.0,
  rollTauS: 0.35,
  maxRollRad: MathUtils.degToRad(6),
  refLatAccelMps2: 4 * G,
  curvatureSpanM: 15,
  fovDeg: 72,
}

export function newFollowState(): FollowState {
  return { sUnwrapped: 0, d: 0, speedMps: 0, carIndex: -1, posed: false, x: 0, z: 0, yawRad: 0, cut: 0, wallMs: Number.NaN, frozen: false }
}

export function newRigState(): RigState {
  return { u: 0, roll: 0, yaw: 0, carIndex: -1, cut: 0 }
}

export function newPose(): CameraPose {
  return { position: new Vector3(), target: new Vector3(), up: new Vector3(0, 1, 0), anchor: new Vector3() }
}

const CURVATURE_TAPS = 7

/** Curvatura em `s` filtrada em distância sobre +/- `spanM`. */
export function smoothCurvature(frame: TrackFrame, s: number, spanM: number): number {
  let sum = 0
  for (let k = 0; k < CURVATURE_TAPS; k++) {
    const t = (k / (CURVATURE_TAPS - 1)) * 2 - 1
    sum += curvatureAt(frame, s + t * spanM)
  }
  return sum / CURVATURE_TAPS
}

/** Inclinação da T-cam pela aceleração lateral `curvatura * v^2`, saturada. */
export function targetRoll(frame: TrackFrame, follow: FollowState, cfg: OnboardConfig): number {
  const lateral = smoothCurvature(frame, follow.sUnwrapped, cfg.curvatureSpanM) * follow.speedMps * follow.speedMps
  return cfg.maxRollRad * MathUtils.clamp(lateral / cfg.refLatAccelMps2, -1, 1)
}

/** Amortecimento de um ângulo pelo arco mais curto, independente da taxa de quadros. */
export function dampAngle(current: number, target: number, tauS: number, dtS: number): number {
  const gap = Math.atan2(Math.sin(target - current), Math.cos(target - current))
  return current + gap * (1 - Math.exp(-dtS / tauS))
}

/**
 * Avança o rig em `dtS`. O termo de antecipação (`u += v dt`) evita que o
 * amortecimento fique `v * tau` atrás de um alvo que anda.
 */
export function stepRig(
  state: RigState,
  frame: TrackFrame,
  follow: FollowState,
  dtS: number,
  chase: ChaseConfig = CHASE,
  onboard: OnboardConfig = ONBOARD,
): void {
  if (follow.carIndex < 0) return

  const roll = targetRoll(frame, follow, onboard)

  if (state.carIndex !== follow.carIndex || state.cut !== follow.cut) {
    state.carIndex = follow.carIndex
    state.cut = follow.cut
    state.u = follow.sUnwrapped - chase.trailM
    state.roll = roll
    state.yaw = follow.yawRad
    return
  }

  const dt = Math.min(Math.max(dtS, 0), MAX_DELTA_S)
  state.u += follow.speedMps * dt
  state.u = MathUtils.damp(state.u, follow.sUnwrapped - chase.trailM, 1 / chase.tauS, dt)
  state.roll = MathUtils.damp(state.roll, roll, 1 / onboard.rollTauS, dt)
  if (follow.posed) state.yaw = dampAngle(state.yaw, follow.yawRad, chase.yawTauS, dt)
}

const view = new Vector3()
const shift = new Vector3()
const forward = new Vector3()

/**
 * Câmera de perseguição. Com pose: atrás do carro na direção suavizada
 * (`state.yaw`), `trailM` atrás e `heightM` acima, mirando `lookaheadM` à
 * frente na mesma direção; o carro fica sempre no eixo da câmera na
 * horizontal. Não lê a pista nem `sUnwrapped`. Sem pose (ou `rig = "track"`):
 * o caminho pela pista, `trackChasePose`.
 */
export function chasePose(
  frame: TrackFrame,
  state: RigState,
  follow: FollowState,
  cfg: ChaseConfig,
  out: CameraPose,
  rig: ChaseRig = "heading",
): CameraPose {
  if (!follow.posed || rig === "track") return trackChasePose(frame, state, follow, cfg, out)
  // Frente do modelo = -Z local: (-sin yaw, 0, -cos yaw) no three.
  forward.set(-Math.sin(state.yaw), 0, -Math.cos(state.yaw))
  out.anchor.set(follow.x, 0, follow.z)
  out.position.copy(out.anchor).addScaledVector(forward, -cfg.trailM)
  out.position.y = cfg.heightM
  out.target.copy(out.anchor).addScaledVector(forward, cfg.lookaheadM)
  out.target.y = cfg.targetHeightM
  out.up.copy(WORLD_UP)
  return out
}

/**
 * O rig de perseguição antigo, portado do viz3d. Direção pela pista
 * (`state.u` atrás, `sUnwrapped` + `lookaheadM` à frente), transladada para
 * que a âncora fique sobre a pose do carro, e limitada a `maxOffAxisRad` do
 * carro.
 */
export function trackChasePose(
  frame: TrackFrame,
  state: RigState,
  follow: FollowState,
  cfg: ChaseConfig,
  out: CameraPose,
): CameraPose {
  toWorld(frame, state.u, follow.d, cfg.heightM, out.position)
  toWorld(frame, follow.sUnwrapped + cfg.lookaheadM, follow.d, cfg.targetHeightM, out.target)
  toWorld(frame, follow.sUnwrapped, follow.d, 0, out.anchor)
  if (follow.posed) {
    shift.set(follow.x - out.anchor.x, 0, follow.z - out.anchor.z)
    out.anchor.add(shift)
    out.position.add(shift)
    out.target.add(shift)
  }
  clampOffAxis(out, cfg.maxOffAxisRad)
  out.up.copy(WORLD_UP)
  return out
}

/** Gira o alvo em torno da vertical da câmera até ficar a no máximo `maxRad` do carro. */
export function clampOffAxis(pose: CameraPose, maxRad: number): void {
  const cx = pose.anchor.x - pose.position.x
  const cz = pose.anchor.z - pose.position.z
  const tx = pose.target.x - pose.position.x
  const tz = pose.target.z - pose.position.z
  const horiz = Math.hypot(tx, tz)
  if (horiz < 1e-6 || Math.hypot(cx, cz) < 1e-6) return
  const toCar = Math.atan2(cx, cz)
  const delta = Math.atan2(Math.sin(Math.atan2(tx, tz) - toCar), Math.cos(Math.atan2(tx, tz) - toCar))
  if (Math.abs(delta) <= maxRad) return
  const yaw = toCar + Math.sign(delta) * maxRad
  pose.target.x = pose.position.x + Math.sin(yaw) * horiz
  pose.target.z = pose.position.z + Math.cos(yaw) * horiz
}

function posedOnboard(follow: FollowState, groundY: number, cfg: OnboardConfig, out: CameraPose) {
  forward.set(-Math.sin(follow.yawRad), 0, -Math.cos(follow.yawRad))
  out.anchor.set(follow.x, groundY, follow.z)
  out.position.copy(out.anchor).addScaledVector(forward, cfg.fwdM)
  out.position.y += cfg.heightM
  out.target.copy(out.anchor).addScaledVector(forward, cfg.lookaheadM)
  out.target.y += cfg.targetHeightM
}

/** T-cam presa à pose do carro; só a inclinação é amortecida. */
export function onboardPose(
  frame: TrackFrame,
  state: RigState,
  follow: FollowState,
  cfg: OnboardConfig,
  out: CameraPose,
): CameraPose {
  toWorld(frame, follow.sUnwrapped, follow.d, 0, out.anchor)
  if (follow.posed) {
    posedOnboard(follow, out.anchor.y, cfg, out)
  } else {
    toWorld(frame, follow.sUnwrapped + cfg.fwdM, follow.d, cfg.heightM, out.position)
    toWorld(frame, follow.sUnwrapped + cfg.lookaheadM, follow.d, cfg.targetHeightM, out.target)
  }
  view.subVectors(out.target, out.position).normalize()
  out.up.copy(WORLD_UP).applyAxisAngle(view, state.roll)
  return out
}
