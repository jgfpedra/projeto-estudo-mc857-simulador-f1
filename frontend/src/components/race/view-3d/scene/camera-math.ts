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
}

export interface RigState {
  /** Comprimento de arco da própria câmera de perseguição; atrasa `trailM`. */
  u: number
  roll: number
  /** Carro para o qual `u` e `roll` foram calculados; -1 = sem semente. */
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
  fovDeg: number
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
  fovDeg: 45,
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
  return { sUnwrapped: 0, d: 0, speedMps: 0, carIndex: -1, posed: false, x: 0, z: 0, yawRad: 0, cut: 0 }
}

export function newRigState(): RigState {
  return { u: 0, roll: 0, carIndex: -1, cut: 0 }
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
    return
  }

  const dt = Math.min(Math.max(dtS, 0), MAX_DELTA_S)
  state.u += follow.speedMps * dt
  state.u = MathUtils.damp(state.u, follow.sUnwrapped - chase.trailM, 1 / chase.tauS, dt)
  state.roll = MathUtils.damp(state.roll, roll, 1 / onboard.rollTauS, dt)
}

const view = new Vector3()
const shift = new Vector3()
const forward = new Vector3()

/**
 * Câmera de perseguição. Direção pela pista (`sUnwrapped` + `lookaheadM`),
 * transladada para que a âncora fique sobre a pose do carro.
 */
export function chasePose(
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
  out.up.copy(WORLD_UP)
  return out
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
