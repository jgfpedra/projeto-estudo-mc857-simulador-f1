/** Signed ground displacement along the car's mean heading, in metres.
 * The engine's progress is a track projection, so it is not a wheel odometer
 * during a slide, reverse manoeuvre, or collision. */
export function signedWheelTravel(x0: number, y0: number, heading0: number, x1: number, y1: number, heading1: number): number {
  const delta = Math.atan2(Math.sin(heading1 - heading0), Math.cos(heading1 - heading0))
  const heading = heading0 + delta / 2
  return (x1 - x0) * Math.cos(heading) + (y1 - y0) * Math.sin(heading)
}
