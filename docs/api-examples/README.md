# API Examples — Verification Status

All three files here were captured directly from a live, running instance of this repository's FastAPI app (via `TestClient`, `GET` requests only — no data was created or modified to produce them) against real run **582** (`water_shortage`, day 7), not hand-written or fabricated:

- `decision-run-example.json` — real `GET /api/decision/tomato/runs/582?day=7` response. Phase 5 is COMPLETE; this example is production-verified.
- `optimization-run-example.json` — real `GET /api/optimization/tomato/runs/582?day=7` response. **Phase 6 status: IMPLEMENTED — FINAL TESTING PENDING.** This JSON is a genuine, correct capture of current backend behavior, but has not been through this project's separate final Phase 6 verification workflow — treat it as implementation-verified, not product-verified.
- `farm-config-example.json` — the same run's stored farm configuration row, formatted to match `FarmConfigurationOut` (read directly from the database, read-only, no write call made to produce this file).

See `docs/API_CONTRACT.md` for the full field-by-field contract and `docs/DEMO_DATA.md` for more real run/day combinations, including the honest `UNAVAILABLE` case (run 584, day 37).
