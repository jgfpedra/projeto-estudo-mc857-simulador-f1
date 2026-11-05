#!/usr/bin/env node
/**
 * Render verification: drive the *built* viewer in headless Chromium and prove
 * it is drawing.
 *
 * Why this exists: the editor's preview pane cannot run `requestAnimationFrame`,
 * so M3, M5 and M6 all closed without anyone seeing motion. This replaces the
 * pane as the way to verify rendering.
 *
 *     npm run snapshot              # build, then run this
 *     node scripts/snapshot.mjs     # against an existing dist/
 *
 * What it does:
 *
 *   1. Serves `dist/` with `vite preview` and loads it with `?probe`, which
 *      mounts `src/probe.tsx` and exposes the WebGL frame counter.
 *   2. Waits until at least 60 frames have been drawn. A counter stuck at zero
 *      fails, and so does any later step that does not advance it.
 *   3. Requires the viewer's own 7 orientation checks to log the verdicts in
 *      `src/track/expected-verdicts.json`, and check J to log PASS. For our
 *      Monza that is all seven PASS. The engine's frozen tracks (phase 0,
 *      docs/phase0-geometry-report.md) have known failures; those are pinned
 *      there and print as XFAIL with the measured value, and a verdict that
 *      changes in *either* direction fails the run.
 *   4. Screenshots every camera mode under every motion source the track has,
 *      and fails any shot whose canvas is (nearly) a single flat colour. The
 *      DOM panels are hidden for that measurement, so they cannot make a blank
 *      canvas pass.
 *   5. Wheel check, at 0.25x, on our Monza (it needs the replay): steps the
 *      clock one 0.25x frame at a time beside a front wheel with the debug
 *      markers on, checks every step's spin against distance travelled, then
 *      scrubs the timeline backwards and requires the marker to come back to
 *      exactly where it was.
 *   6. Then moves to each engine track by clicking its link in the viewer's
 *      own track picker, so the selector is exercised rather than bypassed,
 *      and repeats 2-4 with the synthetic field (no replay exists for them).
 *
 * Output: `.cache/snapshots/*.png` (gitignored). Exit code 1 on any failure.
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { preview } from 'vite'
import { chromium } from 'playwright'

const ROOT = resolve(fileURLToPath(import.meta.url), '..', '..')
const OUT = join(ROOT, '.cache', 'snapshots')

const VIEWPORT = { width: 1280, height: 720 }
const MIN_FRAMES = 60
/** Frames to let a camera settle after a mode or source change. */
const SETTLE_FRAMES = 30
const TIMEOUT_MS = 60_000
/**
 * A canvas fails as "flat" if fewer than this fraction of its pixels differ
 * from its most common colour. The real orbit view, the sparsest shot, is
 * mostly background with a thin ribbon across it, and measures 0.59%; the
 * follow cameras measure 27-40%. A blank canvas - a NaN in the camera
 * position, tested - is exactly 0. The measured values are printed every run,
 * so this can be checked against them rather than trusted.
 */
const MIN_NON_BACKGROUND = 0.001

const MODES = [
  { key: '1', name: 'orbit' },
  { key: '2', name: 'chase' },
  { key: '3', name: 'onboard' },
]
/**
 * One run per track, in this order. The first is loaded by URL; each later one
 * is reached by clicking the previous page's track-picker link.
 */
const RUNS = [
  { track: 'monza', sources: ['synthetic', 'replay'], wheel: true },
  { track: 'monza_v1', sources: ['synthetic'], wheel: false },
  { track: 'interlagos_v2', sources: ['synthetic'], wheel: false },
]

/** The one list of known check failures, shared with src/track/tracks.test.ts. */
const EXPECTED = JSON.parse(readFileSync(join(ROOT, 'src', 'track', 'expected-verdicts.json'), 'utf8'))

/** Wheel check: how many 0.25x frames to step, and at what frame rate. */
const WHEEL_RATE = 0.25
const WHEEL_STEPS = 8
const WHEEL_FPS = 60
const WHEEL_MARKER_HEX = 0xffe600

const failures = []
const fail = (msg) => {
  failures.push(msg)
  console.log(`  FAIL  ${msg}`)
}
const pass = (msg) => console.log(`  PASS  ${msg}`)
const note = (tag, msg) => console.log(`  ${tag.padEnd(5)} ${msg}`)

// ---------------------------------------------------------------------------
// page helpers
// ---------------------------------------------------------------------------

const frames = (page) => page.evaluate(() => window.__viewer?.frames() ?? 0)

/** Wait until `n` more frames have been drawn than `from`. */
async function waitFrames(page, from, n, what) {
  try {
    await page.waitForFunction(
      ([target]) => (window.__viewer?.frames() ?? 0) >= target,
      [from + n],
      { timeout: TIMEOUT_MS, polling: 50 },
    )
    return true
  } catch {
    const now = await frames(page)
    fail(
      now === 0
        ? `${what}: frame count stayed at zero - nothing is rendering`
        : `${what}: frame count stalled at ${now}, wanted ${from + n}`,
    )
    return false
  }
}

/**
 * Screenshot the canvas with every DOM panel hidden, and measure how much of
 * it is not its most common colour. The PNG is decoded in the page, which
 * already has a decoder, rather than pulling one into package.json.
 */
async function measureCanvas(page) {
  await page.evaluate(() => {
    const canvas = document.querySelector('canvas')
    const hidden = []
    for (let el = canvas; el && el !== document.body; el = el.parentElement) {
      for (const sib of el.parentElement?.children ?? []) {
        if (sib !== el && !sib.contains(canvas) && sib.style.visibility !== 'hidden') {
          hidden.push([sib, sib.style.visibility])
          sib.style.visibility = 'hidden'
        }
      }
    }
    window.__snapshotHidden = hidden
  })
  const png = await page.locator('canvas').screenshot()
  await page.evaluate(() => {
    for (const [el, v] of window.__snapshotHidden ?? []) el.style.visibility = v
    delete window.__snapshotHidden
  })
  const stats = await page.evaluate(async (b64) => {
    const img = new Image()
    img.src = `data:image/png;base64,${b64}`
    await img.decode()
    const c = new OffscreenCanvas(img.width, img.height)
    const ctx = c.getContext('2d')
    ctx.drawImage(img, 0, 0)
    const px = new Uint32Array(ctx.getImageData(0, 0, img.width, img.height).data.buffer)
    const counts = new Map()
    for (const v of px) counts.set(v, (counts.get(v) ?? 0) + 1)
    let top = 0
    for (const n of counts.values()) top = Math.max(top, n)
    return { pixels: px.length, colours: counts.size, nonBackground: 1 - top / px.length }
  }, png.toString('base64'))
  return { png, ...stats }
}

/** Pick a camera mode or motion source through the real UI. */
async function pressKey(page, key) {
  await page.evaluate(() => document.activeElement?.blur())
  await page.keyboard.press(key)
}

async function selectSource(page, source) {
  await page.getByRole('button', { name: source, exact: true }).click()
  await page.evaluate(() => document.activeElement?.blur())
}

// ---------------------------------------------------------------------------
// wheel check
// ---------------------------------------------------------------------------

/**
 * Read the followed car's front-wheel marker, in the page.
 *
 * `theta` is the marker's angle about its axle in car-local space, from the
 * instance matrices actually handed to the GPU - not from `wheelAngle`, which
 * would only test the formula against itself.
 */
function readWheelInPage(markerHex) {
  const v = window.__viewer
  const { scene } = v.store()
  const markers = []
  let body = null
  scene.traverse((o) => {
    if (!o.isInstancedMesh) return
    if (o.material?.color?.getHex?.() === markerHex) markers.push(o)
    else if (o.instanceColor && !body) body = o
  })
  if (markers.length === 0 || !body) return null
  const car = v.readout.carIndex < 0 ? 0 : v.readout.carIndex

  const m = new body.matrix.constructor()
  body.getMatrixAt(car, m)
  const c = m.elements.slice()
  // The front wheel is the marker whose hub is furthest along the car's forward
  // (-Z local). Column 2 of the car matrix is car-local +Z in world space.
  let best = null
  for (const mk of markers) {
    mk.getMatrixAt(car, m)
    const w = m.elements.slice()
    const rel = [w[12] - c[12], w[13] - c[13], w[14] - c[14]]
    const fwd = -(rel[0] * c[8] + rel[1] * c[9] + rel[2] * c[10])
    if (!best || fwd > best.fwd) best = { w, rel, fwd }
  }
  const { w, rel } = best
  const col = (e, i) => [e[4 * i], e[4 * i + 1], e[4 * i + 2]]
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
  // The marker's radial direction is wheel-local +Y; express it in car axes.
  const radial = col(w, 1)
  const theta = Math.atan2(dot(radial, col(c, 2)), dot(radial, col(c, 1)))
  const right = col(c, 0)
  const side = Math.sign(dot(rel, right)) || 1
  return {
    theta,
    hub: [w[12], w[13], w[14]],
    outward: right.map((x) => x * side),
    up: col(c, 1),
    sUnwrapped: v.readout.sUnwrapped,
    tS: v.clock.tS,
  }
}

const wrapPi = (a) => Math.atan2(Math.sin(a), Math.cos(a))

async function readWheel(page) {
  return page.evaluate(readWheelInPage, WHEEL_MARKER_HEX)
}

/** Put the orbit camera 2.6 m outboard of the wheel, looking at the hub. */
async function lookAtWheel(page) {
  await page.evaluate(
    ([fnSrc, hex]) => {
      const read = new Function(`return (${fnSrc})`)()
      const w = read(hex)
      const { camera, controls } = window.__viewer.store()
      const p = w.hub.map((h, i) => h + w.outward[i] * 2.6 + w.up[i] * 0.5)
      camera.position.set(p[0], p[1], p[2])
      controls.target.set(w.hub[0], w.hub[1], w.hub[2])
      controls.update()
    },
    [readWheelInPage.toString(), WHEEL_MARKER_HEX],
  )
}

/** Set replay time directly, then let two frames draw it. */
async function setTime(page, tS) {
  await page.evaluate((t) => {
    window.__viewer.clock.tS = t
  }, tS)
  await waitFrames(page, await frames(page), 2, 'wheel step')
}

async function wheelCheck(page) {
  console.log('\n  wheel markers, replay at 0.25x')
  await selectSource(page, 'replay')
  await pressKey(page, '1')
  await page.getByRole('button', { name: `${WHEEL_RATE}x`, exact: true }).click()
  await page.getByText('debug: wheel markers').click()
  await page.evaluate(() => document.activeElement?.blur())
  // Pause through the clock rather than the space key: deterministic steps
  // below need it held still between them.
  await page.evaluate(() => {
    window.__viewer.clock.playing = false
  })

  const radius = 0.3872 // grid.test.ts pins it; used only to scale the check
  const dt = WHEEL_RATE / WHEEL_FPS
  const t0 = 60.2 // mid-race, on a replay sample, and well inside the window

  // A burst of real 0.25x frames, one clock step each, camera re-aimed each time.
  const shots = []
  const reads = []
  for (let k = 0; k <= WHEEL_STEPS; k++) {
    await setTime(page, t0 + k * dt)
    await lookAtWheel(page)
    await waitFrames(page, await frames(page), 2, 'wheel camera')
    reads.push(await readWheel(page))
    shots.push(await page.locator('canvas').screenshot())
  }
  if (reads.some((r) => !r)) {
    fail('wheel: could not find the marker meshes - is the toggle wired?')
    return
  }

  // Each step's spin against the distance the car covered in it. Compared mod
  // 2*pi, so a fast car cannot alias its way past the check.
  let worst = 0
  let forward = 0
  for (let k = 1; k < reads.length; k++) {
    const ds = reads[k].sUnwrapped - reads[k - 1].sUnwrapped
    const dTheta = wrapPi(reads[k].theta - reads[k - 1].theta)
    worst = Math.max(worst, Math.abs(wrapPi(dTheta + ds / radius)))
    if (ds > 0 && dTheta < 0) forward++
  }
  const perFrameDeg = (((reads.at(-1).sUnwrapped - reads[0].sUnwrapped) / WHEEL_STEPS / radius) * 180) / Math.PI
  const msg =
    `${WHEEL_STEPS} steps of 1/${WHEEL_FPS} s at ${WHEEL_RATE}x, ${perFrameDeg.toFixed(1)} deg/frame; ` +
    `spin vs distance worst ${worst.toExponential(1)} rad; ${forward}/${WHEEL_STEPS} steps roll forwards`
  if (worst < 1e-3 && forward === WHEEL_STEPS) pass(`wheel spin: ${msg}`)
  else fail(`wheel spin: ${msg}`)

  // Scrub the timeline backwards through the real slider, which seeks the clock
  // and cuts the camera exactly as a user's drag does.
  const before = reads[0]
  await setTime(page, t0 + 3) // somewhere else first, so the scrub has work to do
  const away = await readWheel(page)
  await page.locator('input[type=range]').fill(String(t0))
  await waitFrames(page, await frames(page), 2, 'scrub')
  await lookAtWheel(page)
  await waitFrames(page, await frames(page), 2, 'scrub camera')
  const back = await readWheel(page)
  shots.push(await page.locator('canvas').screenshot())
  const err = Math.abs(wrapPi(back.theta - before.theta))
  const scrubMsg =
    `scrubbed ${away.tS.toFixed(2)} -> ${back.tS.toFixed(2)} s: marker ` +
    `${((away.theta * 180) / Math.PI).toFixed(1)} -> ${((back.theta * 180) / Math.PI).toFixed(1)} deg, ` +
    `was ${((before.theta * 180) / Math.PI).toFixed(1)} deg at t0 (error ${err.toExponential(1)} rad)`
  if (Math.abs(back.tS - t0) < 1e-9 && err < 1e-6) pass(`wheel rewind: ${scrubMsg}`)
  else fail(`wheel rewind: ${scrubMsg}`)

  shots.forEach((png, k) =>
    writeFileSync(join(OUT, `wheel-${String(k).padStart(2, '0')}${k > WHEEL_STEPS ? '-scrubbed-back' : ''}.png`), png),
  )
  // One contact sheet, cropped to the wheel, so the sequence reads at a glance.
  const sheet = await page.evaluate(async (b64s) => {
    const imgs = await Promise.all(
      b64s.map(async (b) => {
        const i = new Image()
        i.src = `data:image/png;base64,${b}`
        await i.decode()
        return i
      }),
    )
    const crop = 300
    const c = document.createElement('canvas')
    c.width = crop * imgs.length
    c.height = crop
    const ctx = c.getContext('2d')
    imgs.forEach((img, k) => {
      ctx.drawImage(img, (img.width - crop) / 2, (img.height - crop) / 2, crop, crop, k * crop, 0, crop, crop)
      ctx.fillStyle = '#fff'
      ctx.font = '14px monospace'
      ctx.fillText(k < imgs.length - 1 ? `step ${k}` : 'scrubbed back', k * crop + 8, 20)
    })
    return c.toDataURL('image/png').split(',')[1]
  }, shots.map((s) => s.toString('base64')))
  writeFileSync(join(OUT, 'wheel-sheet.png'), Buffer.from(sheet, 'base64'))
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

/**
 * Compare the logged orientation checks with `expected-verdicts.json`.
 * Matching PASS prints PASS; a matching pinned FAIL or SKIP prints XFAIL / SKIP
 * with the viewer's own detail, so the measured value is in every run's output.
 */
function compareVerdicts(track, logs) {
  const summary = logs.map((l) => l.match(/(\d+)\/(\d+) orientation checks passed/)).find(Boolean)
  if (!summary) {
    fail(`${track}: orientation checks were never logged`)
    return
  }
  const want = EXPECTED[track]?.verdicts
  if (!want) {
    fail(`${track}: no entry in src/track/expected-verdicts.json`)
    return
  }
  const got = {}
  for (const l of logs) {
    // A-G only: the viewer logs other lettered lines ([I], [J]) that are not
    // orientation checks. tracks.test.ts asserts the exact set of ids.
    const m = l.match(/^(PASS|FAIL|SKIP) {2}\[([A-G])\] (.*)$/)
    if (m) got[m[2]] = { verdict: m[1], text: m[3] }
  }
  let ok = 0
  for (const id of Object.keys(want)) {
    const g = got[id]
    if (!g) fail(`${track} [${id}]: never logged`)
    else if (g.verdict !== want[id])
      fail(`${track} [${id}]: logged ${g.verdict}, expected-verdicts.json pins ${want[id]} - ${g.text}`)
    else if (g.verdict === 'PASS') ok++
    else note(g.verdict === 'FAIL' ? 'XFAIL' : 'SKIP', `${track} [${id}] ${g.text}`)
  }
  const extra = Object.keys(got).filter((id) => !(id in want))
  if (extra.length) fail(`${track}: checks ${extra.join(', ')} logged but not pinned`)
  pass(`${track}: orientation checks ${summary[1]}/${summary[2]} passed, verdicts as pinned (${ok} PASS)`)
}

async function runTrack(page, run, url, logs) {
  console.log(`\n  track ${run.track}`)
  try {
    await page.waitForFunction(() => !!window.__viewer, null, { timeout: TIMEOUT_MS })
  } catch {
    fail(`${run.track}: probe never mounted: the app did not reach the Canvas (load error?)`)
    return
  }
  const current = new URL(page.url()).searchParams.get('track') ?? 'monza'
  if (current !== run.track) fail(`${run.track}: page is showing track "${current}"`)
  if (!(await waitFrames(page, 0, MIN_FRAMES, `${run.track} startup`))) return
  pass(`${run.track}: render loop: ${await frames(page)} frames drawn`)

  compareVerdicts(run.track, logs)

  if (run.sources.includes('replay')) {
    try {
      await page.waitForFunction(
        () => [...document.querySelectorAll('button')].some((b) => b.textContent === 'replay' && !b.disabled),
        null,
        { timeout: TIMEOUT_MS },
      )
    } catch {
      fail(`${run.track}: replay never loaded, so its button stayed disabled`)
    }
  }

  const rows = []
  for (const source of run.sources) {
    await selectSource(page, source)
    for (const mode of MODES) {
      await pressKey(page, mode.key)
      const from = await frames(page)
      const ok = await waitFrames(page, from, SETTLE_FRAMES, `${run.track}/${source}/${mode.name}`)
      const m = await measureCanvas(page)
      const file = `${run.track}-${source}-${mode.name}.png`
      await page.screenshot({ path: join(OUT, file) })
      const flat = m.nonBackground < MIN_NON_BACKGROUND
      rows.push({ source, mode: mode.name, ok: ok && !flat, ...m, drawn: (await frames(page)) - from, file })
      if (flat)
        fail(
          `${run.track}/${source}/${mode.name}: canvas is a flat colour - ` +
            `${(m.nonBackground * 100).toFixed(3)}% non-background, ${m.colours} colours`,
        )
    }
    const j = logs.find((l) => l.includes('[J]') && l.includes(`${source} source`))
    if (!j) fail(`${run.track}: check J never logged for the ${source} source`)
    else if (!j.startsWith('PASS')) fail(`${run.track}: check J: ${j}`)
  }

  console.log('\n  source     mode      frames  non-bg %  colours  file')
  for (const r of rows) {
    console.log(
      `  ${r.ok ? ' ' : '!'}${r.source.padEnd(10)}${r.mode.padEnd(10)}${String(r.drawn).padStart(6)}` +
        `${(r.nonBackground * 100).toFixed(2).padStart(10)}${String(r.colours).padStart(9)}  ${r.file}`,
    )
  }

  if (run.wheel) await wheelCheck(page)
}

async function main() {
  mkdirSync(OUT, { recursive: true })
  const server = await preview({ root: ROOT, logLevel: 'warn', preview: { port: 4319 } })
  const url = server.resolvedUrls.local[0]
  const browser = await chromium.launch({
    // Headless has no GPU: WebGL goes through SwiftShader, which newer Chromium
    // only allows when asked.
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  })
  try {
    const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 1 })
    // Reset on every navigation, so one track's check lines cannot satisfy the
    // next track's comparison.
    let logs = []
    page.on('console', (m) => logs.push(m.text()))
    page.on('pageerror', (e) => fail(`page error: ${e.message}`))

    console.log(`\n  snapshot  ${url}?probe`)
    console.log('  ' + '-'.repeat(74))
    for (const [k, run] of RUNS.entries()) {
      logs = []
      if (k === 0) {
        await page.goto(`${url}?probe&track=${run.track}`)
      } else {
        // Through the viewer's own picker: the link must keep `probe`.
        const link = page.locator(`a[href*="track=${run.track}"]`)
        const href = await link.getAttribute('href').catch(() => null)
        if (!href) {
          fail(`track picker has no link to ${run.track}`)
          continue
        }
        if (!new URLSearchParams(href.replace(/^\?/, '')).has('probe'))
          fail(`track picker link to ${run.track} drops ?probe: ${href}`)
        await Promise.all([page.waitForURL(`**track=${run.track}**`), link.click()])
      }
      await runTrack(page, run, url, logs)
    }
  } finally {
    await browser.close()
    await new Promise((r) => server.httpServer.close(r))
  }
}

await main()
console.log('  ' + '-'.repeat(74))
console.log(
  failures.length === 0
    ? `  all snapshot checks pass - screenshots in ${OUT}\n`
    : `  ${failures.length} snapshot check(s) FAILED - screenshots in ${OUT}\n`,
)
process.exit(failures.length === 0 ? 0 : 1)
