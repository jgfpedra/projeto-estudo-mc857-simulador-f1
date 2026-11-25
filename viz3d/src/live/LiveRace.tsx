import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Sphere, Vector3 } from 'three'
import { Grid } from '../cars/Grid'
import { PALETTE } from '../cars/field'
import { RACE_CAR_RED } from '../cars/model'
import type { CarIdentity, MotionSource } from '../cars/motion'
import { CameraRig } from '../cameras/CameraRig'
import type { CameraMode, FollowState } from '../cameras/rig'
import { LiveBuffer } from './buffer'
import type { LiveTick } from './buffer'
import { newClock } from '../replay/clock'
import { buildFrame } from '../track/frame'
import { TrackRibbon } from '../track/TrackRibbon'
import { pitLaneFromLive, trackFromLive } from './track'
import { PitLaneRibbon } from './PitLaneRibbon'
import type { LiveTrack } from './track'
import { StartFinishLine } from './StartFinishLine'

type Meta = { race_id: string; num_laps: number; car_geometry?: { length_m: number; width_m: number; height_m: number }; track: LiveTrack; drivers: { driver_id: string; name: string; grid_position: number }[] }
const api = (import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/$/, '')

type AiSuggestion = {
  type: 'ai_suggestion'
  aviso: string
  previsao: { pit_stop_recomendado: boolean; volta_estimada: number | null; composto_sugerido: string | null }
  urgencia: 'baixa' | 'media' | 'alta'
  comando: { tipo: string; valor: number; motivo: string }
  sim_ts: number
  volta: number
  driver_id: string
  resposta_piloto?: string | null
}

export function LiveRace() {
  const [raceId, setRaceId] = useState(() => new URLSearchParams(location.search).get('race') || '')
  const [trackName, setTrackName] = useState('interlagos')
  const [laps, setLaps] = useState(3)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [tick, setTick] = useState<LiveTick | null>(null)
  const [status, setStatus] = useState('')
  const [suggestions, setSuggestions] = useState<AiSuggestion[]>([])
  const buffer = useRef(new LiveBuffer())
  const initial = useRef<Record<string, number>>({})
  const clock = useRef(newClock())
  const readout = useRef<FollowState>({ s: 0, sUnwrapped: 0, d: 0, speedMps: 0, carIndex: -1, posed: false, x: 0, z: 0, yawRad: 0 })
  const [selected, setSelected] = useState(0)
  const [cameraMode, setCameraMode] = useState<CameraMode>('chase')
  const [wheelMarkers, setWheelMarkers] = useState(false)
  const [cutKey, setCutKey] = useState(0)

  useEffect(() => {
    if (!raceId) return
    let disposed = false
    let socket: WebSocket | undefined
    let retry: ReturnType<typeof setTimeout> | undefined
    let finished = false
    async function connect() {
      try {
        setStatus('Conectando…')
        const response = await fetch(`${api}/races/${encodeURIComponent(raceId)}`)
        if (!response.ok) throw new Error(`Corrida indisponível (${response.status})`)
        const data = await response.json() as Meta
        if (disposed) return
        setMeta(data)
        const url = new URL(`/ws/races/${encodeURIComponent(raceId)}`, api)
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        socket = new WebSocket(url)
        socket.onopen = () => setStatus('Ao vivo')
        socket.onmessage = (message) => {
          const event = JSON.parse(message.data)
          if (event.type === 'tick') {
            const next = event as LiveTick
            const previousRevision = buffer.current.revision
            if (!buffer.current.push(next)) return
            if (buffer.current.revision !== previousRevision) setCutKey((key) => key + 1)
            for (const p of next.positions) initial.current[p.driver_id] ??= p.progress_m
            setTick((current) => current ?? next)
          } else if (event.type === 'ai_suggestion') {
            const suggestion = event as AiSuggestion
            setSuggestions((prev) => [suggestion, ...prev.slice(0, 19)]) // keep last 20
          } else if (event.type === 'race_end' || event.type === 'race_error') {
            finished = true
            buffer.current.finish()
            setStatus(event.type === 'race_end' ? 'Corrida encerrada' : `Erro: ${event.message}`)
          }
        }
        socket.onclose = () => {
          if (!disposed && !finished) { buffer.current.disconnected(); setStatus('Conexão perdida; reconectando…'); retry = setTimeout(connect, 2000) }
        }
      } catch (error) {
        if (!disposed) { setStatus(error instanceof Error ? error.message : 'Falha de conexão'); retry = setTimeout(connect, 2000) }
      }
    }
    connect()
    return () => { disposed = true; if (retry) clearTimeout(retry); socket?.close() }
  }, [raceId])

  useEffect(() => {
    if (!raceId) return
    const timer = setInterval(() => {
      const displayed = buffer.current.displayTick(performance.now())
      if (displayed) setTick((current) => current === displayed ? current : displayed)
    }, 50)
    return () => clearInterval(timer)
  }, [raceId])

  const scene = useMemo(() => {
    if (!meta) return null
    const track = trackFromLive(meta.track)
    const frame = buildFrame(track)
    const pitLane = pitLaneFromLive(meta.track.pit_lane)
    const sphere = new Sphere().setFromPoints([...track.points, ...(pitLane?.points ?? [])])
    const distance = sphere.radius / Math.sin(Math.PI / 8) * 1.3
    const cars: CarIdentity[] = [...meta.drivers].sort((a, b) => a.grid_position - b.grid_position).map((driver, index) => ({
      index, label: driver.driver_id, name: driver.name, colourName: PALETTE[index % PALETTE.length].name, hex: PALETTE[index % PALETTE.length].hex,
    }))
    const ids = [...meta.drivers].sort((a, b) => a.grid_position - b.grid_position).map((driver) => driver.driver_id)
    const source: MotionSource = {
      kind: 'engine', cars, durationS: Infinity,
      sampleInto(_time, car, out) {
        return buffer.current.sampleInto(ids[car], performance.now(), out)
      },
      originM(car) { return initial.current[ids[car]] ?? 0 },
    }
    const geometry = meta.car_geometry
    const modelSpec = geometry ? { ...RACE_CAR_RED, dimensions: { lengthM: geometry.length_m, widthM: geometry.width_m, heightM: geometry.height_m } } : RACE_CAR_RED
    return { track, frame, pitLane, cars, source, modelSpec, center: sphere.center, distance, fitted: { target: sphere.center, position: sphere.center.clone().add(new Vector3(0, distance, distance * 0.3)), far: distance * 8 } }
  }, [meta])

  async function start() {
    try {
      setStatus('Criando corrida…')
      const response = await fetch(`${api}/races`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ laps, track: trackName || null }) })
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || `HTTP ${response.status}`) }
      const data = await response.json()
      history.replaceState(null, '', `?live=1&race=${encodeURIComponent(data.race_id)}`)
      setRaceId(data.race_id)
    } catch (error) { setStatus(error instanceof Error ? error.message : 'Erro ao criar corrida') }
  }

  if (!raceId) return <div style={{ padding: 30, color: 'white', background: '#15151e', minHeight: '100vh', fontFamily: 'sans-serif' }}>
    <h1>Corrida ao vivo</h1><label>Pista <input value={trackName} onChange={(e) => setTrackName(e.target.value)} /></label>{' '}
    <label>Voltas <input type="number" min={1} max={200} value={laps} onChange={(e) => setLaps(Number(e.target.value))} /></label>{' '}
    <button onClick={start}>Iniciar corrida</button><p>{status}</p><a href="/">Visualização de gravações</a>
  </div>
  if (!scene || !tick) return <div style={{ padding: 30, color: 'white', background: '#15151e', minHeight: '100vh' }}>{status || 'Aguardando primeiro estado da corrida…'}</div>
  const urgencyColor = (u: string) => u === 'alta' ? '#ff4444' : u === 'media' ? '#ffaa00' : '#44ff44'

  return <div style={{ position: 'fixed', inset: 0, background: '#15151e' }}>
    <Canvas camera={{ position: [scene.center.x, scene.distance, scene.center.z + scene.distance * 0.3], fov: 45, near: 1, far: scene.distance * 8 }}>
      <hemisphereLight args={['#ffffff', '#30303c', 1.1]} /><directionalLight position={[600, 1200, 400]} intensity={1.2} />
      <TrackRibbon frame={scene.frame} widthM={scene.track.widthM} />
      {scene.pitLane && <PitLaneRibbon lane={scene.pitLane} />}
      <StartFinishLine track={scene.track} />
      <Suspense fallback={null}>
        <Grid frame={scene.frame} cars={scene.cars} source={scene.source} modelSpec={scene.modelSpec} clock={clock} selected={selected} readout={readout} wheelMarkers={wheelMarkers} />
        <CameraRig frame={scene.frame} mode={cameraMode} readout={readout} fitted={scene.fitted} orbitFovDeg={45} clock={clock} cutKey={cutKey} />
      </Suspense>
    </Canvas>
    <div style={{ position: 'absolute', top: 12, left: 12, color: 'white', background: '#15151ee8', padding: 12, font: '14px sans-serif', maxWidth: 380 }}>
      <strong>{scene.track.name} · {status}</strong>
      {scene.pitLane && <div style={{ color: '#c4c4cd' }}>Via dos boxes{scene.pitLane.source === 'estimated' ? ' (estimada)' : ''}</div>}
      <div style={{ marginTop: 8 }}>
        <button onClick={() => setCameraMode('chase')}>Seguir</button>{' '}
        <button onClick={() => setCameraMode('onboard')}>A bordo</button>{' '}
        <button onClick={() => setCameraMode('orbit')}>Pista</button>{' '}
        <button onClick={() => setWheelMarkers((enabled) => !enabled)}>{wheelMarkers ? 'Ocultar marcas' : 'Marcar rodas'}</button>
      </div>
      <div style={{ marginTop: 8 }}>Tempo: {tick.sim_ts.toFixed(1)} s</div>
      {tick.positions.map((p) => <div key={p.driver_id} style={{ marginTop: 4 }}><button onClick={() => { setSelected(scene.cars.findIndex((c) => c.label === p.driver_id)); setCutKey((key) => key + 1) }} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', textAlign: 'left', padding: 0 }}>{p.position}. {p.driver_id}</button> · {Math.round(p.velocity_mps * 3.6)} km/h · volta {p.lap + 1}</div>)}
      {tick.collisions?.length > 0 && <div style={{ marginTop: 4, color: '#ffaa00' }}>Contato: {tick.collisions[0].drv_a} / {tick.collisions[0].drv_b}</div>}
    </div>

    {/* Engenheiro / AI suggestions panel */}
    <div style={{ position: 'absolute', top: 12, right: 12, width: 360, maxHeight: '60vh', color: 'white', background: '#15151ee8', padding: 12, font: '13px monospace', overflow: 'auto', border: '1px solid #333', borderRadius: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, borderBottom: '1px solid #333', paddingBottom: 4 }}>
        <strong>📻 Engenheiro (IA)</strong>
        <span style={{ color: '#888', fontSize: '11px' }}>{suggestions.length} mensagens</span>
      </div>
      {suggestions.length === 0 ? (
        <div style={{ color: '#666', textAlign: 'center', padding: '20px 0' }}>Aguardando sugestões do engenheiro…</div>
      ) : (
        suggestions.map((s, i) => (
          <div key={i} style={{ marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid #222' }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
              <span style={{ color: urgencyColor(s.urgencia), fontWeight: 'bold', textTransform: 'uppercase', fontSize: '10px' }}>{s.urgencia}</span>
              <span style={{ color: '#888', fontSize: '10px' }}>T+{s.sim_ts.toFixed(1)}s · Volta {s.volta}</span>
              <span style={{ color: '#888', fontSize: '10px' }}>{s.driver_id}</span>
            </div>
            <div style={{ color: '#ffeb3b', marginBottom: 4 }}>"{s.aviso}"</div>
            <div style={{ display: 'flex', gap: 12, fontSize: '11px', color: '#aaa', flexWrap: 'wrap' }}>
              <span>Comando: <span style={{ color: '#fff' }}>{s.comando.tipo}</span> ({s.comando.valor})</span>
              <span>Motivo: <span style={{ color: '#fff' }}>{s.comando.motivo}</span></span>
            </div>
            {s.previsao.pit_stop_recomendado && (
              <div style={{ marginTop: 4, color: '#ff44ff', fontSize: '11px' }}>
                🛑 Pit recomendado · Volta ~{s.previsao.volta_estimada ?? '?'} · {s.previsao.composto_sugerido ?? '?'}
              </div>
            )}
            {s.resposta_piloto && (
              <div style={{ marginTop: 4, color: '#ff6b6b', fontSize: '11px', fontStyle: 'italic', borderLeft: '2px solid #ff6b6b', paddingLeft: 8 }}>
                🗣️ Piloto: "{s.resposta_piloto}"
              </div>
            )}
          </div>
        ))
      )}
    </div>
  </div>
}
