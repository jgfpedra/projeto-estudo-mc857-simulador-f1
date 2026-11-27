import { after, before, test } from "node:test"
import assert from "node:assert/strict"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { createServer } from "vite"

let server
let TimingPanel
let AiFloatingPanel
let DriverFollowCard

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: "custom", logLevel: "silent" })
  ;({ TimingPanel } = await server.ssrLoadModule("/src/components/race/timing-panel.tsx"))
  ;({ AiFloatingPanel } = await server.ssrLoadModule("/src/components/race/ai/ai-floating-panel.tsx"))
  ;({ DriverFollowCard } = await server.ssrLoadModule("/src/components/race/driver-follow-card.tsx"))
})

after(async () => {
  await server?.close()
})

const driver = {
  driverId: "laf",
  abbreviation: "LAF",
  name: "Laf",
  number: 1,
  team: "Equipe",
  teamColor: "#ffffff",
  teamColorSource: "openf1",
  gridPosition: 1,
}
const race = { raceId: "race-1", numLaps: 3, track: { name: "Interlagos" }, drivers: [driver] }
const car = {
  driverId: "laf",
  position: 1,
  lap: 0,
  speedKmh: 52,
  tyre: "MEDIUM",
  tyreLifePct: 100,
  pitting: false,
  gapToLeaderS: null,
  lapsBehind: 0,
}
const frame = { simTs: 1, lap: 0, weather: null, cars: [car] }
const noop = () => {}

function timingProps(overrides = {}) {
  return {
    race,
    frame,
    prevFrame: null,
    classification: null,
    selectedDriverId: null,
    followedDriverId: null,
    onSelect: noop,
    onFollow: noop,
    onUnfollow: noop,
    ...overrides,
  }
}

function findButton(node, label) {
  if (!node || typeof node !== "object") return null
  if (node.type === "button" && node.props["aria-label"] === label) return node
  const children = React.Children.toArray(node.props?.children)
  for (const child of children) {
    const found = findButton(child, label)
    if (found) return found
  }
  return null
}

test("classification keeps the whole driver card clickable and highlights the selected row in red", () => {
  for (const classification of [null, [{ position: 1, driverId: "laf", lapsCompleted: 3, totalTimeS: 65, pitStops: 0 }]]) {
    const selectedHtml = renderToStaticMarkup(React.createElement(TimingPanel, timingProps({
      classification,
      selectedDriverId: "laf",
    })))
    assert.match(selectedHtml, /aria-label="Selecionar LAF" aria-pressed="true"/)
    assert.match(selectedHtml, /bg-primary\/20 ring-2 ring-inset ring-primary/)

    const buttonStart = selectedHtml.indexOf('<button type="button" aria-label="Selecionar LAF"')
    const buttonEnd = selectedHtml.indexOf("</button>", buttonStart)
    const selectButton = selectedHtml.slice(buttonStart, buttonEnd)
    assert.ok(buttonStart >= 0 && buttonEnd > buttonStart)
    for (const content of ["01", "LAF", classification ? "01:05.0" : "LÍDER"]) {
      assert.ok(selectButton.includes(content), `${content} deve fazer parte da área clicável`)
    }

    const unselectedHtml = renderToStaticMarkup(React.createElement(TimingPanel, timingProps({ classification })))
    assert.match(unselectedHtml, /aria-label="Selecionar LAF" aria-pressed="false"/)
    assert.doesNotMatch(unselectedHtml, /bg-primary\/20 ring-2 ring-inset ring-primary/)
  }
})

test("selecting and deselecting a timing row calls onSelect with the expected driver", () => {
  const calls = []
  const element = TimingPanel(timingProps({ onSelect: (driverId) => calls.push(driverId) }))
  const button = findButton(element, "Selecionar LAF")
  assert.ok(button)
  button.props.onClick()

  const selectedElement = TimingPanel(timingProps({
    selectedDriverId: "laf",
    onSelect: (driverId) => calls.push(driverId),
  }))
  findButton(selectedElement, "Selecionar LAF").props.onClick()
  assert.deepEqual(calls, ["laf", null])
})

test("AI panel uses normal flow below the followed driver instead of fixed positioning", () => {
  const props = {
    engineerStatus: "monitoring",
    raceId: "race-1",
    raceName: "Interlagos",
    suggestions: [],
    commands: new Map(),
  }
  const inline = renderToStaticMarkup(React.createElement(AiFloatingPanel, { ...props, position: "inline" }))
  assert.match(inline, /relative mt-3 w-full min-w-0 shrink-0/)
  assert.doesNotMatch(inline, /fixed top-4 right-4/)

  const floating = renderToStaticMarkup(React.createElement(AiFloatingPanel, { ...props, position: "top-right" }))
  assert.match(floating, /fixed top-4 right-4/)
})

test("race page shows monitoring only while following a driver and keeps the card below the viewer header", async () => {
  const { RaceSimulation } = await server.ssrLoadModule("/src/pages/race-simulation.tsx")
  const { useLiveRaceStore } = await server.ssrLoadModule("/src/stores/live-race-store.ts")
  const previousState = useLiveRaceStore.getState()
  const originalUseSyncExternalStore = React.useSyncExternalStore
  // No SSR, o Zustand usa o estado inicial; para este teste, use o estado atual da store.
  React.useSyncExternalStore = (_subscribe, getSnapshot) => getSnapshot()

  const renderPage = () => renderToStaticMarkup(React.createElement(MemoryRouter, {
    initialEntries: ["/race-simulation/race-1"],
  }, React.createElement(Routes, null, React.createElement(Route, {
    path: "/race-simulation/:raceId",
    element: React.createElement(RaceSimulation),
  }))))

  try {
    useLiveRaceStore.setState({
      status: "live",
      race: { ...race, userDriverId: null, track: { name: "Interlagos", waypoints: [] } },
      frame: null,
      prevFrame: null,
      classification: null,
      followedDriverId: null,
      selectedDriverId: null,
      viewMode: "2d",
      feed: [],
      aiSuggestions: [],
      aiCommands: new Map(),
      aiEngineerStatus: "monitoring",
    })
    assert.doesNotMatch(renderPage(), /Painel do Engenheiro de IA/)

    useLiveRaceStore.getState().followDriver("laf")
    const followedHtml = renderPage()
    assert.match(followedHtml, /Painel do Engenheiro de IA/)
    assert.match(followedHtml, /absolute bottom-6 left-6 top-16/)
    assert.doesNotMatch(followedHtml, /fixed top-4 right-4/)

    useLiveRaceStore.getState().unfollowDriver()
    assert.doesNotMatch(renderPage(), /Painel do Engenheiro de IA/)
  } finally {
    useLiveRaceStore.setState(previousState, true)
    React.useSyncExternalStore = originalUseSyncExternalStore
  }
})

test("followed driver card renders the monitoring panel after its data and last event", () => {
  const feed = [{
    id: 1,
    simTs: 1,
    lap: 1,
    kind: "race_control",
    tone: "info",
    message: "🟡 Engenheiro (LAF): Defenda a posição!",
    driverIds: ["laf"],
  }]
  const html = renderToStaticMarkup(React.createElement(DriverFollowCard, {
    race,
    frame,
    prevFrame: null,
    feed,
    classification: null,
    driverId: "laf",
  }, React.createElement("div", null, "MONITORANDO")))

  const tyreIndex = html.indexOf("Pneu")
  const eventIndex = html.indexOf("🟡 Engenheiro (LAF): Defenda a posição!")
  const monitoringIndex = html.indexOf("MONITORANDO")
  assert.ok(tyreIndex >= 0 && eventIndex > tyreIndex)
  assert.ok(monitoringIndex > eventIndex, "MONITORANDO deve ficar abaixo de todo o card do piloto")
})
