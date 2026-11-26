"use client"

import { useFrame } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import { Color, ConeGeometry, Group, MeshBasicMaterial, RingGeometry, SphereGeometry, Vector3 } from "three"
import type { AiSuggestion, AiCommand } from "@/types/race"

interface Props {
  /** Histórico de sugestões do engenheiro. */
  suggestions: AiSuggestion[]
  /** Comando ativo por driverId. */
  commands: Map<string, AiCommand>
  /** Driver seguido atualmente. */
  followedDriverId: string | null
  /** Posição mundial onde o engenheiro fica (acima da linha S/F). */
  position: Vector3
  /** Status do ciclo de vida: "idle" | "started" | "monitoring" | "stopped" | "error" */
  engineerStatus?: "idle" | "started" | "monitoring" | "stopped" | "error"
}

/**
 * Engenheiro de IA 3D — orb holográfico flutuante acima da linha de chegada.
 * - Cor reflete urgência da última mensagem (verde/amarelo/vermelho)
 * - Brilha quando há comando ativo
 * - Animação de hover suave
 * - Estado do ciclo de vida afeta aparência (pulsação, cor base)
 */
export function AiEngineer({ suggestions, commands, followedDriverId, position, engineerStatus = "idle" }: Props) {
  const groupRef = useRef<Group>(null)
  const pulsePhase = useRef(0)

  // Cor baseada no status do engenheiro + urgência da última mensagem
  const baseColor = useMemo(() => {
    // Prioridade: error > status do ciclo de vida > urgência da última sugestão
    if (engineerStatus === "error") return new Color("#ff5252") // vermelho
    if (engineerStatus === "stopped") return new Color("#6b7280") // cinza
    if (engineerStatus === "started") return new Color("#3b82f6") // azul
    if (engineerStatus === "monitoring") return new Color("#3ecf5a") // verde

    // Fallback: urgência da última sugestão
    const last = suggestions[suggestions.length - 1]
    if (!last) return new Color("#3ecf5a")
    switch (last.urgency) {
      case "alta":
        return new Color("#ff5252")
      case "media":
        return new Color("#ffb020")
      case "baixa":
        return new Color("#9a9aa8")
      default:
        return new Color("#3ecf5a")
    }
  }, [suggestions, engineerStatus])

  // Se há comando ativo para o driver seguido
  const hasActiveCommand = useMemo(() => {
    if (!followedDriverId) return false
    const cmd = commands.get(followedDriverId)
    return cmd && cmd.command !== "neutral"
  }, [commands, followedDriverId])

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

    // Pulsing scale - mais intenso quando monitoring/started
    const pulseSpeed = engineerStatus === "monitoring" || engineerStatus === "started" ? 2.5 : 1.5
    const pulseAmp = engineerStatus === "monitoring" ? 0.12 : 0.08
    const pulse = 1 + Math.sin(pulsePhase.current * pulseSpeed) * pulseAmp
    group.scale.setScalar(pulse)

    // Update material colors
    const color = baseColor
    if (ringMatRef.current) {
      ringMatRef.current.color.lerp(color, 0.1)
      // Opacidade do anel indica estado
      let targetOpacity = 0.3
      if (engineerStatus === "monitoring") targetOpacity = 0.5
      else if (engineerStatus === "started") targetOpacity = 0.6
      else if (engineerStatus === "error") targetOpacity = 0.7
      else if (engineerStatus === "stopped") targetOpacity = 0.2

      if (hasActiveCommand) targetOpacity = Math.min(1, targetOpacity + 0.3)

      ringMatRef.current.opacity = ringMatRef.current.opacity + (targetOpacity - ringMatRef.current.opacity) * 0.1
    }
    if (coreMatRef.current) {
      coreMatRef.current.color.lerp(color, 0.1)
      // Core mais brilhante quando ativo
      const targetCoreOpacity = engineerStatus === "monitoring" ? 0.8 : (engineerStatus === "stopped" ? 0.5 : 0.7)
      coreMatRef.current.opacity = coreMatRef.current.opacity + (targetCoreOpacity - coreMatRef.current.opacity) * 0.1
    }
    if (coneMatRef.current) {
      coneMatRef.current.color.lerp(color, 0.1)
      coneMatRef.current.opacity = hasActiveCommand
        ? Math.min(0.8, coneMatRef.current.opacity + delta * 2)
        : Math.max(0.3, coneMatRef.current.opacity - delta)
    }
  })

  // Indicador visual de status (pequena esfera colorida no topo)
  const statusIndicatorColor = useMemo(() => {
    switch (engineerStatus) {
      case "error": return new Color("#ff5252")
      case "stopped": return new Color("#6b7280")
      case "started": return new Color("#3b82f6")
      case "monitoring": return new Color("#3ecf5a")
      default: return new Color("#6b7280")
    }
  }, [engineerStatus])

  return (
    <group ref={groupRef} position={position.clone()}>
      {/* Outer pulsing ring */}
      <mesh geometry={ringGeom} rotation={[-Math.PI / 2, 0, 0]}>
        <meshBasicMaterial
          ref={ringMatRef}
          transparent
          opacity={0.3}
          color={baseColor}
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
          color={baseColor}
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

      {/* Directional indicator - a thin cone pointing up */}
      <mesh geometry={coneGeom} position={[0, 1.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <meshBasicMaterial
          ref={coneMatRef}
          transparent
          opacity={0.5}
          color={baseColor}
          depthWrite={false}
        />
      </mesh>

      {/* Status indicator - small sphere at top */}
      <mesh
        geometry={new SphereGeometry(0.15, 8, 8)}
        position={[0, 2.0, 0]}
      >
        <meshBasicMaterial
          transparent
          opacity={0.9}
          color={statusIndicatorColor}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}