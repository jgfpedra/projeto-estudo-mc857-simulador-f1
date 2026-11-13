"""Cut the committed fixture out of a full engine recording.

Phase 3, step 2. Full recordings live in `.cache/recordings/` (gitignored, ~7.6
MB for three laps); the viewer and the tests read a trimmed copy committed under
`public/recordings/`. This keeps the race block unchanged apart from a
`recording.trimmed` note, and takes contiguous ticks from `--from-s` for as
long as the file stays under `--max-bytes`.

    python scripts/trim_recording.py .cache/recordings/interlagos_seed42_3laps.jsonl \
        --out public/recordings/engine-interlagos-seed42.jsonl

The default window starts at the first tick: the start is where the field is
bunched and most of the overtaking happens, and for seed 42 the first ~41 s also
hold Sainz's one off-track excursion (39.6-40.8 s, |d| up to 9.2 m), so the
fixture exercises the off-track path as well as the on-track one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("recording", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--from-s", type=float, default=0.0)
    ap.add_argument("--max-bytes", type=int, default=1_000_000)
    args = ap.parse_args()

    raw = args.recording.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    header = json.loads(lines[0])
    ticks = [line for line in lines[1:] if line.strip()]
    start = next(i for i, line in enumerate(ticks) if json.loads(line)["sim_ts"] >= args.from_s - 1e-9)

    def render(n: int) -> bytes:
        h = json.loads(lines[0])
        h.setdefault("recording", {})["trimmed"] = {
            "from": str(args.recording.as_posix()),
            "from_sha256": hashlib.sha256(raw).hexdigest()[:16],
            "from_ticks": len(ticks),
            "first_tick": start,
            "ticks": n,
        }
        body = [json.dumps(h, separators=(",", ":"))] + ticks[start:start + n]
        return ("\n".join(body) + "\n").encode("utf-8")

    lo, hi = 2, len(ticks) - start
    if len(render(lo)) > args.max_bytes:
        raise SystemExit("the race block alone does not fit")
    while lo < hi:                      # largest n that fits
        mid = (lo + hi + 1) // 2
        if len(render(mid)) <= args.max_bytes:
            lo = mid
        else:
            hi = mid - 1
    out = render(lo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(out)
    first = json.loads(ticks[start])["sim_ts"]
    last = json.loads(ticks[start + lo - 1])["sim_ts"]
    print(f"{args.out}: {len(out)} bytes, {lo} ticks, sim_ts {first}..{last} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
