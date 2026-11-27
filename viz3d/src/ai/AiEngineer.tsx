import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import { Color, ConeGeometry, Group, MeshBasicMaterial, RingGeometry, SphereGeometry, Vector3 } from 'three'
import { speechSynthesis } from './SpeechSynthesis'

/** Minimal store interface needed by AiEngineer. */
interface EngineerStore {
  messages: readonly { urgencia?: string; aviso?: string }[]
  trackEvents: readonly unknown[]
  meta: { drivers: { driver_id: string }[] }
  latestRow: (index: number) => { position_xy?: [number, number] } | undefined
  activeCommand: (index: number) => { command: string } | null
}

interface Props {
  store: EngineerStore
  /** World position where the engineer hovers. */
  position: Vector3
  /** The car being followed — the engineer "watches" this car. */
  followedIndex: number
}

/**
 * 3D representation of the AI race engineer.
 *
 * A floating holographic orb with a pulsing ring that sits above the circuit
 * (by default over the start/finish line). It subtly turns toward the followed
 * car and its colour reflects the urgency of the most recent message.
 */
export function AiEngineer({ store, position, followedIndex }: Props) {
  const groupRef = useRef<Group>(null)
  const pulsePhase = useRef(0)
  const targetYaw = useRef(0)
  const currentYaw = useRef(0)
  const lastSpokenIndex = useRef(store.messages.length - 1)

  // O gerenciador serializa a fila e elimina duplicatas também enviadas pelo AiPanel.
  useEffect(() => {
    const messages = store.messages
    const lastIndex = messages.length - 1
    const prevIndex = lastSpokenIndex.current

    if (lastIndex > prevIndex) {
      for (let i = prevIndex + 1; i <= lastIndex; i++) {
        const msg = messages[i]
        if (msg?.aviso) {
          const urgency = msg.urgencia === 'alta' || msg.urgencia === 'baixa' ? msg.urgencia : 'media'
          speechSynthesis.speak(msg.aviso, urgency)
        }
      }
      lastSpokenIndex.current = lastIndex
    }
  }, [store.messages])

  // Colours matching the urgency palette in AiPanel
  const urgencyColor = useMemo(() => {
    const last = store.messages[store.messages.length - 1]
    if (!last) return new Color('#3ecf5a') // default green
    switch (last.urgencia) {
      case 'alta':
        return new Color('#ff5252')
      case 'media':
        return new Color('#ffb020')
      case 'baixa':
        return new Color('#9a9aa8')
      default:
        return new Color('#3ecf5a')
    }
  }, [store.messages])

  // Command state for visual feedback
  const hasActiveCommand = useMemo(() => {
    const cmd = store.activeCommand(followedIndex)
    return cmd && cmd.command !== 'neutral'
  }, [store.trackEvents, followedIndex])

  // Pre-create geometries
  const ringGeom = useMemo(() => new RingGeometry(1.2, 1.8, 32), [])
  const coreGeom = useMemo(() => new SphereGeometry(0.6, 16, 16), [])
  const glowGeom = useMemo(() => new SphereGeometry(0.3, 8, 8), [])
  const coneGeom = useMemo(() => new ConeGeometry(0.15, 0.8, 8), [])

  // Material refs for updating
  const ringMatRef = useRef<MeshBasicMaterial>(null)
  const coreMatRef = useRef<MeshBasicMaterial>(null)
  const coneMatRef = useRef<MeshBasicMaterial>(null)

  useFrame((_, delta) => {
    const group = groupRef.current
    if (!group) return

    // Gentle hover animation
    pulsePhase.current += delta * 1.5
    const hover = Math.sin(pulsePhase.current) * 0.3
    group.position.y = position.y + hover

    // Pulsing scale
    const pulse = 1 + Math.sin(pulsePhase.current * 2) * 0.08
    group.scale.setScalar(pulse)

    // Turn toward the followed car (smoothed)
    // LivePosition has position_xy: [x, y] in engine plan coordinates
    // trackFromLive converts to three.js as (x, 0, -y)
    const row = store.latestRow(followedIndex)
    if (row && row.position_xy) {
      const targetX = row.position_xy[0]
      const targetZ = -row.position_xy[1]
      const dx = targetX - position.x
      const dz = targetZ - position.z
      targetYaw.current = Math.atan2(dx, dz)
    }

    // Smooth rotation
    const diff = targetYaw.current - currentYaw.current
    currentYaw.current += diff * 0.05
    group.rotation.y = currentYaw.current

    // Update material colors
    const color = urgencyColor
    if (ringMatRef.current) {
      ringMatRef.current.color.lerp(color, 0.1)
      ringMatRef.current.opacity = hasActiveCommand
        ? Math.min(1, ringMatRef.current.opacity + delta * 2)
        : Math.max(0.4, ringMatRef.current.opacity - delta)
    }
    if (coreMatRef.current) {
      coreMatRef.current.color.lerp(color, 0.1)
    }
    if (coneMatRef.current) {
      coneMatRef.current.color.lerp(color, 0.1)
      coneMatRef.current.opacity = hasActiveCommand
        ? Math.min(0.8, coneMatRef.current.opacity + delta * 2)
        : Math.max(0.3, coneMatRef.current.opacity - delta)
    }
  })

  return (
    <group ref={groupRef} position={position.clone()}>
      {/* Outer pulsing ring */}
      <mesh geometry={ringGeom} rotation={[-Math.PI / 2, 0, 0]}>
        <meshBasicMaterial
          ref={ringMatRef}
          transparent
          opacity={0.3}
          color={urgencyColor}
          side={2}
          depthWrite={false}
        />
      </mesh>

      {/* Core sphere */}
      <mesh geometry={coreGeom}>
        <meshBasicMaterial
          ref={coreMatRef}
          transparent
          opacity={0.7}
          color={urgencyColor}
          depthWrite={false}
        />
      </mesh>

      {/* Inner glow */}
      <mesh geometry={glowGeom}>
        <meshBasicMaterial
          transparent
          opacity={0.9}
          color="#ffffff"
          depthWrite={false}
        />
      </mesh>

      {/* Directional indicator - a thin cone pointing toward followed car */}
      <mesh geometry={coneGeom} position={[0, 1.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <meshBasicMaterial
          ref={coneMatRef}
          transparent
          opacity={0.5}
          color={urgencyColor}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}