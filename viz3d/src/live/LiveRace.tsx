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
import { trackFromLive } from './track'
import type { LiveTrack } from './track'
import { StartFinishLine } from './StartFinishLine'

type Meta = { race_id: string; num_laps: number; car_geometry?: { length_m: number; width_m: number; height_m: number }; track: LiveTrack; drivers: { driver_id: string; name: string; grid_position: number }[] }
const api = (import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/$/, '')

export function LiveRace() {
  const [raceId, setRaceId] = useState(() => new URLSearchParams(location.search).get('race') || '')
  const [trackName, setTrackName] = useState('interlagos')
  const [laps, setLaps] = useState(3)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [tick, setTick] = useState<LiveTick | null>(null)
  const [status, setStatus] = useState('')
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
    const sphere = new Sphere().setFromPoints(track.points)
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
    return { track, frame, cars, source, modelSpec, center: sphere.center, distance, fitted: { target: sphere.center, position: sphere.center.clone().add(new Vector3(0, distance, distance * 0.3)), far: distance * 8 } }
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
  return <div style={{ position: 'fixed', inset: 0, background: '#15151e' }}>
    <Canvas camera={{ position: [scene.center.x, scene.distance, scene.center.z + scene.distance * 0.3], fov: 45, near: 1, far: scene.distance * 8 }}>
      <hemisphereLight args={['#ffffff', '#30303c', 1.1]} /><directionalLight position={[600, 1200, 400]} intensity={1.2} />
      <TrackRibbon frame={scene.frame} widthM={scene.track.widthM} />
      <StartFinishLine track={scene.track} />
      <Suspense fallback={null}>
        <Grid frame={scene.frame} cars={scene.cars} source={scene.source} modelSpec={scene.modelSpec} clock={clock} selected={selected} readout={readout} wheelMarkers={wheelMarkers} />
        <CameraRig frame={scene.frame} mode={cameraMode} readout={readout} fitted={scene.fitted} orbitFovDeg={45} clock={clock} cutKey={cutKey} />
      </Suspense>
    </Canvas>
    <div style={{ position: 'absolute', top: 12, left: 12, color: 'white', background: '#15151ee8', padding: 12, font: '14px sans-serif' }}>
      <strong>{scene.track.name} · {status}</strong><div>
        <button onClick={() => setCameraMode('chase')}>Seguir</button>{' '}
        <button onClick={() => setCameraMode('onboard')}>A bordo</button>{' '}
        <button onClick={() => setCameraMode('orbit')}>Pista</button>{' '}
        <button onClick={() => setWheelMarkers((enabled) => !enabled)}>{wheelMarkers ? 'Ocultar marcas' : 'Marcar rodas'}</button>
      </div><div>Tempo: {tick.sim_ts.toFixed(1)} s</div>
      {tick.positions.map((p) => <div key={p.driver_id}><button onClick={() => { setSelected(scene.cars.findIndex((c) => c.label === p.driver_id)); setCutKey((key) => key + 1) }}>{p.position}. {p.driver_id}</button> · {Math.round(p.velocity_mps * 3.6)} km/h · volta {p.lap + 1}</div>)}
      {tick.collisions?.length > 0 && <div>Contato: {tick.collisions[0].drv_a} / {tick.collisions[0].drv_b}</div>}
    </div>
  </div>
}
