#!/usr/bin/env node
/**
 * Live check of the frontend's 3D race view (frontend/src/components/race/view-3d/),
 * in headless Chrome driven by this package's Playwright. It talks to the running
 * apps over HTTP only; nothing outside viz3d/ is imported.
 *
 * How to run
 *
 *   1. Backend (WSL): Redis, then `cd backend && uvicorn api.main:app --port 8000`.
 *   2. Frontend (dev server, so the `window.__race3d` hook exists): `cd frontend && npm run dev`.
 *   3. From viz3d/:
 *
 *        node scripts/check-3d-frontend.mjs                    # setup flow -> new race -> all checks
 *        node scripts/check-3d-frontend.mjs --race <id>        # reuse a running race
 *        node scripts/check-3d-frontend.mjs --race <id> --only-agreement   # 3D vs 2D positions only
 *
 * Options (flag, or environment variable; flags win):
 *
 *   --frontend <url>  F1_FRONTEND_URL  frontend origin          (default http://localhost:5173)
 *   --api <url>       F1_API_URL       backend origin           (default http://localhost:8000)
 *   --cars <n>        F1_CHECK_CARS    drivers kept in the race (default 10)
 *   --laps <n>        F1_CHECK_LAPS    laps entered in the setup flow (default 5)
 *   --circuit <name>  F1_CHECK_CIRCUIT circuit name as listed in the setup flow (default "José Carlos Pace")
 *   --chrome <path>   CHROME_PATH      Chrome executable; without it, Playwright's installed-Chrome
 *                                      channel ("chrome") is used
 *   --gpu             F1_CHECK_GPU=1   render on the GPU (ANGLE/D3D11) instead of SwiftShader
 *   --quality <q>     F1_CHECK_QUALITY 3D scenery quality: high | low | off. Preset in localStorage
 *                                      ("race3d.quality") before the page loads; without it the page
 *                                      picks its own default (high on a GPU, off on software WebGL,
 *                                      i.e. off under the default SwiftShader)
 *   --out <dir>       F1_CHECK_OUT     screenshots + report.json (default viz3d/.cache/check-3d-frontend)
 *   --toggles <n>     F1_CHECK_TOGGLES 2D/3D toggles in the resource check (default 10)
 *
 * The setup flow always sends a 20-driver grid (GRID_SIZE = 20 in the frontend), so the
 * script trims the outgoing POST /races grid to --cars drivers and keeps the rest of the
 * request as the UI built it.
 *
 * Determinism: every screenshot and the position read-out that goes with it happen with the 3D
 * clock frozen (window.__race3d.freeze(): cars hold the pose of that instant, the WebSocket and
 * the 2D keep running), after the camera has settled; then the clock is unfrozen. So the marker
 * colour and chase-centring checks do not depend on how fast the page renders. For the marker
 * colours (and the click that follows) the script freezes at an instant when no marker covers
 * another one on screen, retrying every 0.5 s for up to 4 minutes (cars nose to tail just after
 * the start overlap); the wait is printed and kept in report.json (markerWait).
 *
 * Checks: 3D-drawn positions (read back from the instance matrices) equal the 2D
 * interpolation within 0.5 m at the same sampled sim time (the 3D plays back ~150 ms behind
 * the newest tick; the hook evaluates interpolateCars at the sim time the 3D drew, from its own
 * copy of the store's frames), with the buffered playback on; one car per driver; overview,
 * chase and onboard canvases not blank; each driver's marker visible in its colour;
 * clicking a car follows it; Esc and "Visão geral" return to the overview; 10x (--toggles)
 * 2D/3D toggles with no console errors or WebGL warnings (e.g. "Blit feedback loop"), every
 * context released and the same GPU resource counts. Exit code 1 on any failure.
 */
import { mkdirSync, writeFileSync } from "node:fs"
import { join, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { chromium } from "playwright"

const ROOT = resolve(fileURLToPath(import.meta.url), "..", "..")
const args = process.argv.slice(2)
const opt = (flag, env, fallback) => {
  const i = args.indexOf(flag)
  if (i >= 0 && args[i + 1] !== undefined) return args[i + 1]
  return process.env[env] || fallback
}
const strip = (url) => url.replace(/\/$/, "")

const BASE = strip(opt("--frontend", "F1_FRONTEND_URL", "http://localhost:5173"))
const API = strip(opt("--api", "F1_API_URL", "http://localhost:8000"))
const N_CARS = Number(opt("--cars", "F1_CHECK_CARS", "10"))
const LAPS = String(Number(opt("--laps", "F1_CHECK_LAPS", "5")))
const CIRCUIT = opt("--circuit", "F1_CHECK_CIRCUIT", "José Carlos Pace")
const CHROME = opt("--chrome", "CHROME_PATH", "")
const OUT = resolve(opt("--out", "F1_CHECK_OUT", join(ROOT, ".cache", "check-3d-frontend")))
const argRace = opt("--race", "F1_CHECK_RACE", null)
const GPU = args.includes("--gpu") || process.env.F1_CHECK_GPU === "1"
const QUALITY = opt("--quality", "F1_CHECK_QUALITY", null)
if (QUALITY !== null && !["high", "low", "off"].includes(QUALITY)) throw new Error(`--quality must be high, low or off, got ${QUALITY}`)
const onlyAgreement = args.includes("--only-agreement")
const TOGGLES = Number(opt("--toggles", "F1_CHECK_TOGGLES", "10"))
if (!Number.isInteger(TOGGLES) || TOGGLES < 1) throw new Error(`--toggles must be a positive integer, got ${TOGGLES}`)
const TOLERANCE_M = 0.5
if (!Number.isInteger(N_CARS) || N_CARS < 1 || N_CARS > 24) throw new Error(`--cars must be 1..24, got ${N_CARS}`)
mkdirSync(OUT, { recursive: true })

const failures = []
const report = { checks: [] }
const check = (name, ok, detail) => {
  report.checks.push({ name, ok, detail })
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail !== undefined ? `  ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : ""}`)
  if (!ok) failures.push(name)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function measureCanvas(page, file) {
  const canvas = page.locator('[data-testid="race-view-3d"] canvas')
  // Hide the page's overlays so they cannot make a blank canvas pass.
  await page.evaluate(() => {
    const c = document.querySelector('[data-testid="race-view-3d"] canvas')
    const hidden = []
    for (let el = c; el && el !== document.body; el = el.parentElement)
      for (const sib of el.parentElement?.children ?? [])
        if (sib !== el && !sib.contains(c) && sib.style.visibility !== "hidden") {
          hidden.push([sib, sib.style.visibility])
          sib.style.visibility = "hidden"
        }
    window.__hidden = hidden
  })
  const png = await canvas.screenshot()
  await page.evaluate(() => {
    for (const [el, v] of window.__hidden ?? []) el.style.visibility = v
    delete window.__hidden
  })
  writeFileSync(join(OUT, file), png)
  const stats = await page.evaluate(async (b64) => {
    const img = new Image()
    img.src = `data:image/png;base64,${b64}`
    await img.decode()
    const c = new OffscreenCanvas(img.width, img.height)
    const ctx = c.getContext("2d")
    ctx.drawImage(img, 0, 0)
    const px = new Uint32Array(ctx.getImageData(0, 0, img.width, img.height).data.buffer)
    const counts = new Map()
    for (const v of px) counts.set(v, (counts.get(v) ?? 0) + 1)
    let top = 0
    let topV = 0
    for (const [v, n] of counts) if (n > top) { top = n; topV = v }
    return { width: img.width, height: img.height, colours: counts.size, nonBackground: 1 - top / px.length, background: topV }
  }, png.toString("base64"))
  return { png, ...stats }
}

/** RGB at canvas CSS px (x, y), searching a small window for the best match to `hex`. */
async function colourNear(page, png, x, y, hex, radius = 3) {
  return page.evaluate(
    async ({ b64, x, y, hex, radius }) => {
      const img = new Image()
      img.src = `data:image/png;base64,${b64}`
      await img.decode()
      const c = new OffscreenCanvas(img.width, img.height)
      const ctx = c.getContext("2d")
      ctx.drawImage(img, 0, 0)
      const want = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
      const scale = img.width / document.querySelector('[data-testid="race-view-3d"] canvas').getBoundingClientRect().width
      let best = Infinity
      let bestRgb = null
      for (let dy = -radius; dy <= radius; dy++)
        for (let dx = -radius; dx <= radius; dx++) {
          const px = Math.round((x + dx) * scale)
          const py = Math.round((y + dy) * scale)
          if (px < 0 || py < 0 || px >= img.width || py >= img.height) continue
          const d = ctx.getImageData(px, py, 1, 1).data
          const dist = Math.hypot(d[0] - want[0], d[1] - want[1], d[2] - want[2])
          if (dist < best) { best = dist; bestRgb = [d[0], d[1], d[2]] }
        }
      return { dist: best, rgb: bestRgb }
    },
    { b64: png.toString("base64"), x, y, hex, radius },
  )
}

async function frames(page, n) {
  await page.evaluate((n) => new Promise((res) => {
    let k = 0
    const step = () => (++k >= n ? res() : requestAnimationFrame(step))
    requestAnimationFrame(step)
  }), n)
}

/**
 * Freeze the 3D clock and let the camera settle: at least `ms` of wall time and `n` frames
 * (the rig clamps each step to 0.1 s, so slow frames still advance it).
 */
async function freeze(page, ms = 2500, n = 30) {
  await page.evaluate(() => window.__race3d.freeze())
  const t0 = Date.now()
  await frames(page, n)
  const left = ms - (Date.now() - t0)
  if (left > 0) await sleep(left)
  await frames(page, 2)
}
const unfreeze = (page) => page.evaluate(() => window.__race3d?.unfreeze())

/**
 * Freeze at an instant when no car marker covers another marker's centre on screen. Cars running
 * nose to tail put markers on top of each other (a geometry fact, not a rendering one), and the
 * colour check needs every marker uncovered. Freezes, measures the markers' screen separation
 * against their projected radius, and if two overlap unfreezes and retries every 0.5 s, up to
 * `timeoutMs`. Returns how long it waited and the separation it froze at.
 */
async function freezeSeparated(page, n, timeoutMs = 240_000) {
  const t0 = Date.now()
  let best = { minPx: 0, radiusPx: 0 }
  for (let attempt = 1; ; attempt++) {
    await freeze(page, 300, 3)
    const pins = (await page.evaluate(() => window.__race3d.screen())).filter((c) => c.pin?.onScreen)
    const radiusPx = Math.max(0, ...pins.map((c) => c.pinRadiusPx ?? 0))
    let minPx = Infinity
    for (let i = 0; i < pins.length; i++)
      for (let j = i + 1; j < pins.length; j++)
        minPx = Math.min(minPx, Math.hypot(pins[i].pin.x - pins[j].pin.x, pins[i].pin.y - pins[j].pin.y))
    const waitedS = Math.round((Date.now() - t0) / 100) / 10
    if (pins.length === n && minPx >= radiusPx + 2) return { waitedS, attempts: attempt, minPx: Math.round(minPx * 10) / 10, radiusPx: Math.round(radiusPx * 10) / 10 }
    if (minPx > best.minPx) best = { minPx: Math.round(minPx * 10) / 10, radiusPx: Math.round(radiusPx * 10) / 10 }
    if (Date.now() - t0 > timeoutMs) return { timedOut: true, waitedS, attempts: attempt, best }
    await unfreeze(page)
    await sleep(500)
  }
}

/**
 * 3D-drawn positions vs the 2D interpolation at the sim time the 3D drew (`sample()`), over
 * `samples` frames. Also reports the playback mode and how far behind the newest tick it ran.
 */
async function agreement(page, label, samples = 40) {
  let worst = 0
  let carsSeen = new Set()
  let counts = []
  const lags = []
  const playback = new Set()
  for (let i = 0; i < samples; i++) {
    await frames(page, 2)
    const s = await page.evaluate(() => window.__race3d?.sample())
    if (!s) continue
    worst = Math.max(worst, s.maxErrorM)
    counts.push(s.cars.length)
    lags.push(s.lagMs)
    playback.add(s.playback)
    s.cars.forEach((c) => carsSeen.add(c.driverId))
  }
  const r = (v) => Math.round(v)
  return {
    label,
    worstErrorM: worst,
    samples: counts.length,
    carsPerSample: [Math.min(...counts), Math.max(...counts)],
    distinctCars: carsSeen.size,
    playback: [...playback],
    lagMs: lags.length ? { min: r(Math.min(...lags)), mean: r(lags.reduce((a, b) => a + b, 0) / lags.length), max: r(Math.max(...lags)) } : null,
  }
}
const buffered = (a) => a.playback.length === 1 && a.playback[0] === "buffered"

async function main() {
  const browser = await chromium.launch({
    ...(CHROME ? { executablePath: CHROME } : { channel: "chrome" }),
    headless: true,
    args: GPU ? ["--use-angle=d3d11", "--ignore-gpu-blocklist"] : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
  })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
  const consoleLines = []
  page.on("console", (m) => consoleLines.push({ type: m.type(), text: m.text() }))
  page.on("pageerror", (e) => consoleLines.push({ type: "pageerror", text: e.message }))
  if (QUALITY) await page.addInitScript((q) => localStorage.setItem("race3d.quality", q), QUALITY)
  // Count WebGL contexts created and lost.
  await page.addInitScript(() => {
    window.__gl = { created: 0, lost: 0 }
    const orig = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
      const ctx = orig.call(this, type, ...rest)
      if (ctx && /webgl/i.test(type) && !this.__glCounted) {
        this.__glCounted = true
        window.__gl.created++
        this.addEventListener("webglcontextlost", () => window.__gl.lost++)
      }
      return ctx
    }
  })

  let raceId = argRace
  if (!raceId) {
    // --- normal setup flow ---
    let sentGrid = null
    await page.route("**/races", async (route) => {
      const req = route.request()
      if (req.method() !== "POST") return route.continue()
      const body = JSON.parse(req.postData())
      sentGrid = { fromUi: body.grid.length, sent: N_CARS }
      // The UI requires a 20-car grid (GRID_SIZE = 20); keep the first N_CARS of it.
      body.grid = body.grid.slice(0, N_CARS)
      report.postBody = body
      await route.continue({ postData: JSON.stringify(body) })
    })
    await page.goto(BASE)
    await page.getByRole("button", { name: /Iniciar/ }).first().click()
    await page.getByPlaceholder("Buscar circuito ou país...").fill(CIRCUIT)
    await page.getByText(CIRCUIT, { exact: true }).first().click()
    await page.getByRole("textbox", { name: "voltas da corrida" }).fill(LAPS)
    await page.getByRole("button", { name: "Confirmar" }).click()
    await page.waitForURL("**/driver-team-selection")
    // "Aleatório" picks from the season's driver list; on a cold backend that list arrives late and a
    // click before it fills nothing. Click again until the grid is complete (up to 120 s).
    for (const t0 = Date.now(); ; ) {
      await page.getByText("Aleatório", { exact: true }).click()
      const done = await page.getByText("Grid completo", { exact: false }).waitFor({ timeout: 5_000 }).then(() => true, () => false)
      if (done) break
      if (Date.now() - t0 > 120_000) throw new Error("random grid never completed (driver list not loaded?)")
    }
    await page.getByRole("button", { name: /Clima \/ Pneus/ }).click()
    await page.waitForURL("**/weather-tires-selection")
    const start = page.getByRole("button", { name: /Iniciar Corrida/ })
    await start.waitFor()
    await page.waitForFunction(() => {
      const b = [...document.querySelectorAll("button")].find((x) => /Iniciar Corrida/i.test(x.textContent ?? ""))
      return b && !b.disabled
    }, null, { timeout: 120_000 })
    await start.click()
    await page.waitForURL("**/race-simulation/**", { timeout: 180_000 })
    raceId = page.url().split("/race-simulation/")[1]
    check("setup flow created the race", Boolean(raceId), { raceId, grid: sentGrid })
  } else {
    await page.goto(`${BASE}/race-simulation/${raceId}`)
  }

  const meta = await (await fetch(`${API}/races/${raceId}`)).json()
  report.race = {
    raceId,
    sources: meta.sources,
    track: { name: meta.track.name, source: meta.track.source, length_m: meta.track.length_m, width_m: meta.track.width_m, waypoints: meta.track.waypoints.length, start_finish_waypoint: meta.track.start_finish_waypoint, pit_lane: meta.track.pit_lane ? { points: meta.track.pit_lane.waypoints.length, source: meta.track.pit_lane.source } : null },
    car_geometry: meta.car_geometry,
    drivers: meta.drivers.map((d) => ({ id: d.driver_id, color: d.team_color, source: d.team_color_source ?? null })),
  }
  const nDrivers = meta.drivers.length
  console.log(`race ${raceId}: ${nDrivers} drivers, track_source=${meta.sources?.track_source}, ${meta.track.waypoints.length} waypoints`)

  // Live ticks flowing.
  await page.getByText("Ao vivo").first().waitFor({ timeout: 120_000 })
  await page.waitForFunction(async () => true)
  // Let the field spread out a little after the start.
  if (!argRace) await sleep(20_000)

  // --- 3D ---
  await page.getByRole("button", { name: "3D", exact: true }).click()
  await page.waitForFunction(() => window.__race3d && document.querySelector('[data-testid="race-view-3d"] canvas'), null, { timeout: 60_000 })
  await frames(page, 60)
  const env = await page.evaluate(() => {
    // From the 3D view's own context: no extra WebGL context (the toggle check counts them).
    const st = window.__race3d.state()
    return { quality: st.quality, softwareRendering: st.environment?.softwareRendering ?? null, renderer: st.renderer ?? null }
  })
  report.render = { gpuFlag: GPU, requestedQuality: QUALITY, ...env }
  console.log(`renderer: ${env.renderer}; 3D quality: ${env.quality}${QUALITY ? " (requested)" : " (page default)"}`)
  if (QUALITY && env.quality !== QUALITY) throw new Error(`requested --quality ${QUALITY}, the page runs ${env.quality}`)

  const agree = await agreement(page, "overview")
  check(`3D drawn positions match 2D within ${TOLERANCE_M} m at the 3D's sim time (overview)`, agree.worstErrorM <= TOLERANCE_M && buffered(agree), agree)
  check("one car per driver in the 3D", agree.carsPerSample[0] === nDrivers && agree.carsPerSample[1] === nDrivers, { drivers: nDrivers, ...agree })
  if (onlyAgreement) return finish(browser)

  const markerWait = await freezeSeparated(page, nDrivers)
  report.markerWait = markerWait
  console.log(`markers separated after ${markerWait.waitedS} s (${markerWait.attempts} freezes): ${JSON.stringify(markerWait)}`)
  await freeze(page)
  const ov = await measureCanvas(page, "overview.png")
  check("overview canvas is not blank", ov.nonBackground > 0.001, { nonBackground: ov.nonBackground, colours: ov.colours, size: [ov.width, ov.height] })
  const scr = await page.evaluate(() => window.__race3d.screen())
  const pinRows = []
  for (const c of scr) {
    if (!c.pin) { pinRows.push({ id: c.driverId, ok: false, why: "no pin" }); continue }
    const m = await colourNear(page, ov.png, c.pin.x, c.pin.y, c.color, 3)
    pinRows.push({ id: c.driverId, color: c.color, onScreen: c.pin.onScreen, at: [Math.round(c.pin.x), Math.round(c.pin.y)], dist: Math.round(m.dist), rgb: m.rgb, ok: c.pin.onScreen && m.dist < 40 })
  }
  report.pins = pinRows
  const pinsOk = pinRows.filter((r) => r.ok).length
  // Pins can overlap when cars run nose to tail; report which ones were hidden.
  check("each driver's marker visible in its colour on the overview", pinsOk === nDrivers, { visible: pinsOk, drivers: nDrivers, hidden: pinRows.filter((r) => !r.ok).map((r) => r.id) })

  // Click a car (its marker) -> onSelectDriver(id) -> chase camera.
  const box = await page.locator('[data-testid="race-view-3d"] canvas').boundingBox()
  // Fresh positions (the pixel checks above took seconds; the cars moved), and the
  // marker farthest from any other so the click is unambiguous.
  const fresh = (await page.evaluate(() => window.__race3d.screen())).filter((c) => c.pin?.onScreen)
  const isolation = (c) => Math.min(...fresh.filter((o) => o !== c).map((o) => Math.hypot(o.pin.x - c.pin.x, o.pin.y - c.pin.y)))
  const target = fresh.sort((a, b) => isolation(b) - isolation(a))[0]
  report.click = { target: target.driverId, isolationPx: Math.round(isolation(target)) }
  await page.mouse.click(box.x + target.pin.x, box.y + target.pin.y)
  await frames(page, 10)
  await unfreeze(page)
  let st = await page.evaluate(() => window.__race3d.state())
  check("clicking a car selects and follows it", st.followed === target.driverId && st.mode === "chase", { clicked: target.driverId, ...st })
  await sleep(1500)
  await frames(page, 30)
  const agreeFollow = await agreement(page, "chase", 20)
  check(`3D matches 2D within ${TOLERANCE_M} m at the 3D's sim time (following)`, agreeFollow.worstErrorM <= TOLERANCE_M && buffered(agreeFollow), agreeFollow)
  await freeze(page)
  const ch = await measureCanvas(page, "followed-chase.png")
  check("chase canvas is not blank", ch.nonBackground > 0.05, { nonBackground: ch.nonBackground, colours: ch.colours })
  const followedScreen = (await page.evaluate(() => window.__race3d.screen())).find((c) => c.driverId === target.driverId)
  const carPx = await colourNear(page, ch.png, followedScreen.car.x, followedScreen.car.y, "#000000", 2)
  const bg = [(ch.background) & 255, (ch.background >> 8) & 255, (ch.background >> 16) & 255]
  check("followed car is on screen near the centre", followedScreen.car.onScreen && Math.abs(followedScreen.car.x / box.width - 0.5) < 0.2, { car: followedScreen.car, pixel: carPx.rgb, background: bg })
  await unfreeze(page)

  // Onboard.
  await page.getByRole("button", { name: "A bordo" }).click()
  await frames(page, 40)
  await freeze(page)
  const ob = await measureCanvas(page, "followed-onboard.png")
  await unfreeze(page)
  st = await page.evaluate(() => window.__race3d.state())
  check("onboard camera renders", st.mode === "onboard" && ob.nonBackground > 0.05, { mode: st.mode, nonBackground: ob.nonBackground })
  await page.getByRole("button", { name: "Perseguição" }).click()

  // Leaving follow from the canvas (Esc) -> onSelectDriver(null) -> overview.
  await page.keyboard.press("Escape")
  await frames(page, 10)
  st = await page.evaluate(() => window.__race3d.state())
  check("Esc leaves follow (selection null, overview)", st.followed === null && st.mode === "orbit", st)

  // Timing panel selection + the page's "Visão geral" button.
  await page.locator("aside button").first().click()
  await frames(page, 10)
  st = await page.evaluate(() => window.__race3d.state())
  const followedFromPanel = st.followed
  await page.getByRole("button", { name: /Visão geral/ }).click()
  await frames(page, 10)
  st = await page.evaluate(() => window.__race3d.state())
  check("timing-panel selection follows; 'Visão geral' returns to overview", followedFromPanel !== null && st.followed === null && st.mode === "orbit", { followedFromPanel, after: st })
  await frames(page, 30)
  await freeze(page)
  await measureCanvas(page, "overview-after.png")
  await unfreeze(page)

  // --- Toggle 2D/3D TOGGLES times ---
  const before = await page.evaluate(() => ({ gl: { ...window.__gl }, state: window.__race3d.state() }))
  const consoleMark = consoleLines.length
  for (let i = 0; i < TOGGLES; i++) {
    await page.getByRole("button", { name: "2D", exact: true }).click()
    await page.waitForFunction(() => !document.querySelector('[data-testid="race-view-3d"]'))
    await frames(page, 15)
    await page.getByRole("button", { name: "3D", exact: true }).click()
    await page.waitForFunction(() => window.__race3d && document.querySelector('[data-testid="race-view-3d"] canvas'))
    await frames(page, 30)
  }
  const afterIn3d = await page.evaluate(() => ({ gl: { ...window.__gl }, state: window.__race3d.state() }))
  await page.getByRole("button", { name: "2D", exact: true }).click()
  await page.waitForFunction(() => !document.querySelector('[data-testid="race-view-3d"]'))
  await sleep(500)
  const afterIn2d = await page.evaluate(() => ({ gl: { ...window.__gl }, canvases: document.querySelectorAll("canvas").length, probe: Boolean(window.__race3d) }))
  const toggleLines = consoleLines.slice(consoleMark)
  const bad = toggleLines.filter((l) => l.type === "error" || l.type === "pageerror" || /webgl|context/i.test(l.text))
  report.toggle = { before, afterIn3d, afterIn2d, consoleDuringToggle: toggleLines.length, bad }
  check(`${TOGGLES}x 2D/3D toggle: no console errors or WebGL/context warnings`, bad.length === 0, bad.slice(0, 5))
  check(`${TOGGLES}x toggle: every context created is released (0 live in 2D)`, afterIn2d.gl.created - afterIn2d.gl.lost === 0 && afterIn2d.canvases === 0, afterIn2d)
  check(
    `${TOGGLES}x toggle: same GPU resource counts on mount ${TOGGLES + 1} as on the 1st`,
    JSON.stringify(afterIn3d.state.memory) === JSON.stringify(before.state.memory) && afterIn3d.state.programs === before.state.programs,
    { first: before.state.memory, firstPrograms: before.state.programs, last: afterIn3d.state.memory, lastPrograms: afterIn3d.state.programs },
  )

  return finish(browser)

  async function finish(b) {
    const errs = consoleLines.filter((l) => l.type === "error" || l.type === "pageerror")
    report.consoleErrors = errs
    report.failures = failures
    writeFileSync(join(OUT, onlyAgreement ? "report-agreement.json" : "report.json"), JSON.stringify(report, null, 2))
    await b.close()
    console.log(failures.length ? `\n${failures.length} FAILED: ${failures.join("; ")}` : "\nall checks passed")
    process.exit(failures.length ? 1 : 0)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(2)
})
