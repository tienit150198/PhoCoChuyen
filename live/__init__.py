"""Phố Có Chuyện live service: chat, online presence (phase 1), strolling the phố (phase 2) and in-game dates
(phase 3) over one WebSocket per open tab. `python3 -m live` (live/app.py). Design:
docs/superpowers/specs/2026-09-30-live-chat-street-design.md; plan and extension points:
docs/superpowers/plans/2026-10-01-live-chat-v1.md.

It never reads or writes a save. It needs the `websockets` library (vendored into shared/pyvendor,
scripts/vendor_websockets.sh) and psycopg 3 with a PostgreSQL DATABASE_URL."""
PROTOCOL = 1
