# Vendored engine frozen tracks

Byte-exact copies of the simulation engine's frozen tracks, vendored so that
viz3d's Phase 0 reproduction (docs/phase0-geometry-report.md) never reads
outside `viz3d/`. Read-only: never edit these; re-copy from the origin instead.
`.gitattributes` marks them `-text` so no checkout rewrites their line endings.

Origin, for both files:

- repo: `projeto-estudo-mc857-simulador-f1` (this repo)
- branch: `feat/bot-ai`
- commit: `cf6529f86350f7fa443377827673737a1cc44780`
- copied with `git cat-file blob cf6529f:<path>` on 2026-11-04

| file | origin path | git blob | engine `sha256` field | file sha256 (blob bytes, LF) |
|---|---|---|---|---|
| `Monza_v1.json` | `backend/model_train/tracks_frozen/Monza_v1.json` | `245490bdea37ef6c8ed8d950191ee4bfe2d0af6e` | `6ed5fac92bc2fb17` | `1fa327814cf042b6c1c460017ac89f3d00b27dfffd9e3fc0567b710195a28e37` |
| `interlagos_v2.json` | `backend/model_train/tracks_frozen/interlagos_v2.json` | `3cac8de851fd992c960e3193ef36e6ce9edac0cc` | `164876196eb12174` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |

The two hashes are different things. The engine `sha256` field is the engine's own
integrity hash (`load_track_frozen` in `backend/model_train/f1_env.py`): the first 16
hex digits of sha256 over the document minus that field, dumped with sorted
keys. It doesn't depend on line endings. The file sha256 is a hash of the raw bytes.

**interlagos_v2 file sha256 caveat.** `public/tracks/interlagos_v2.json`
records `fileSha256: a200320115e53ed058dd53330be28862645cecc5f11767423da97a33970e5cf6`.
That is the hash of the same blob checked out with CRLF line endings
(`core.autocrlf=true` on Windows), not of the blob bytes. Monza_v1 is a single
line, so its two values coincide. The git blob and the engine field are the
checkout-independent identifiers.
