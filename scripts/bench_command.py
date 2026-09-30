#!/usr/bin/env python3
"""CPU cost of one POST /api/command, measured in-process through the real server code.

Each timed command goes through the whole path a player's click takes on a worker: an HTTP
request on a local socket pair handled by server.Handler (headers, cookie, CSRF check, body
parse, rate limit), Store.command (read the save, parse it, apply the action, validate what
changed, serialize, write the save + receipt), the public view, the JSON response, gzip and
the X-Game-Version header (server.game_version, i.e. the static-asset snapshot).

Saves of about 100 / 300 / 1000 KB are grown by playing the engine (several careers, many
days: journals, feeds, tasks, histories), then each benchmark action is set up on it (its
career open, a task in the right step) and the save is stored stamped by this build, as a
save that is played every day is. Before each timed command the save row is put back, so
every iteration runs the same command on the same save.

  python scripts/bench_command.py                     # all sizes x all actions, SQLite in a temp dir
  python scripts/bench_command.py --sizes 300 --actions gr_scan --iters 50
  python scripts/bench_command.py --profile 300:gr_scan   # + cProfile top list of that case
  DATABASE_URL=postgresql://... python scripts/bench_command.py   # the same on PostgreSQL

CPU ms = median CPU time of the thread running the command (Python, SQLite, compression;
time.thread_time, or the thread cycle counter on Windows); wall ms also includes waiting
for PostgreSQL when DATABASE_URL is set. --cpu N pins the process to one logical CPU.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import os
import pstats
import socket
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QUIET", "1")  # no access log lines on stderr
os.environ.setdefault("COMMANDS_PER_MINUTE", "100000000")
os.environ.setdefault("SLOW_COMMAND_MS", "1000000")  # no [slow-cmd] / [slow-write] lines

import server  # noqa: E402
from game import storage, webassets  # noqa: E402,F401
try:
    from game import fastjson  # noqa: E402
except ImportError:
    fastjson = None
from game.engine import GameError, apply_action, new_state, tree_copy, validate_state  # noqa: E402
from game.employment import hired_record, required  # noqa: E402
from game.storage import Store, serialize  # noqa: E402

ACTIONS = {  # benchmark action -> career
    "tea_add": "milk_tea",
    "gr_scan": "grocery",
    "fl_pick": "florist",
    "pc_inspect": "pet_care",
    "dl_ride": "delivery",
}
# Careers played (in this order, round after round) to grow a save.
GROW = ["milk_tea", "grocery", "florist", "pet_care", "delivery", "restaurant", "salon", "homestay",
        "pet_shop", "repair", "farm", "cafe_bakery", "clothing", "tra_da"]


def _dump(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


def _act(state: dict, career, action: str, **payload):
    """(new state, result) or (state, GameError)."""
    try:
        return apply_action(state, career, action, payload, owned=True)
    except GameError as e:
        return state, e


def grow(target_kb: int) -> dict:
    """A save of about target_kb KB, grown by playing days in rotating careers."""
    s = new_state()
    for career in GROW:
        if required(career):
            s["careers"][career]["job"] = hired_record(career)
    days = 0
    while len(_dump(s).encode()) < target_kb * 1024:
        career = GROW[days % len(GROW)] if target_kb > 150 else GROW[days % 2]
        s, _ = _act(s, career, "select_career")
        for _ in range(3):  # three days at a time in each career
            s, _ = _act(s, career, "start_day")
            for _ in range(6):
                s, _ = _act(s, career, "advance")
                s, _ = _act(s, career, "more_work")
            s, _ = _act(s, career, "end_day", carry_event=True)
            if len(_dump(s).encode()) >= target_kb * 1024:
                break
        days += 1
    return s


def _task(s: dict, career: str) -> dict | None:
    c = s["careers"][career]
    return next((t for t in c["tasks"] if t["id"] == c["active_task"]), None)


def _ok(s: dict, career: str, action: str, payload: dict) -> bool:
    try:
        apply_action(tree_copy(s), career, action, payload)
        return True
    except GameError:
        return False


def prepare(base: dict, bench: str) -> tuple[dict, dict]:
    """(save, payload): `bench` succeeds on this save with this payload."""
    career = ACTIONS[bench]
    s = tree_copy(base)
    s, _ = _act(s, career, "select_career")
    for day in range(12):  # a day with an incident waiting for a decision blocks the counter: try the next day
        if s["careers"][career]["open"]:
            s, _ = _act(s, career, "end_day", carry_event=True)
        s, r = _act(s, career, "start_day")
        for attempt in range(4):
            t = _task(s, career)
            if t is None:
                s, _ = _act(s, career, "more_work")
                continue
            s, _ = _act(s, career, "ask", task=t["id"])
            t = _task(s, career)
            found = _candidates(s, career, bench, t)
            if found is not None:
                return found
            s, _ = _act(s, career, "more_work")
            c = s["careers"][career]
            others = [x for x in c["tasks"] if x["status"] not in ("completed", "referred", "cancelled") and x["id"] != c["active_task"]]
            if others:
                s, _ = _act(s, career, "task_select", task=others[-1]["id"])
    raise SystemExit(f"could not set up {bench} on this save")


def _candidates(s: dict, career: str, bench: str, t: dict):
    """(state after any set-up steps, payload) for which `bench` succeeds, or None."""
    if bench == "tea_add":
        from game import boba
        x = tree_copy(s)
        for _ in range(12):
            try:
                action, payload = boba.next_move(x["careers"][career], _task(x, career))
            except Exception:  # noqa: BLE001
                return None
            if action == "tea_add" and _ok(x, career, action, payload):
                return x, payload
            x, r = _act(x, career, action, **payload)
            if isinstance(r, GameError):
                return None
        return None
    if bench == "gr_scan":
        for line in t.get("needs", {}).get("lines", []):
            if not line.get("weighed"):
                payload = dict(task=t["id"], item=line["item"], qty=1)
                if _ok(s, career, bench, payload):
                    return s, payload
        return None
    if bench == "fl_pick":
        from game.careers import florist
        wanted = [k for k in florist.FLOWERS if k in json.dumps(t.get("needs", {}))] + list(florist.FLOWERS)
        for item in wanted:
            payload = dict(task=t["id"], item=item)
            if _ok(s, career, bench, payload):
                return s, payload
        return None
    if bench == "pc_inspect":
        for part in ("scale", "coat", "skin", "ears", "nails", "mood", "eyes", "teeth", "weight"):
            payload = dict(task=t["id"], part=part)
            if _ok(s, career, bench, payload):
                return s, payload
        return None
    if bench == "dl_ride":
        from game.careers import delivery
        for node in delivery.NODES:
            x = tree_copy(s)
            x, r = _act(x, career, "dl_plan", route=[node])
            if not isinstance(r, GameError) and _ok(x, career, "dl_ride", {}):
                return x, {}
        return None
    raise ValueError(bench)


def stamped_text(s: dict) -> str:
    """The save as a server stores it after a fully validated command (build stamp + digests)."""
    s = tree_copy(s)
    s.pop("check", None)
    validate_state(s)
    return serialize(s, None, True)


class Bench:
    def __init__(self, folder: str):
        self.store = Store(Path(folder) / "bench.db")
        self.srv = server.GameServer(("127.0.0.1", 0), self.store)
        self.token, self.csrf, _ = self.store.session()
        self.sid = self.store.key(self.token)
        self.n = 0

    def close(self):
        self.srv.server_close()

    def put(self, text: str, revision: int):
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET state=?,revision=? WHERE sid=?", (text, revision, self.sid))
            db.execute("DELETE FROM receipts WHERE sid=?", (self.sid,))

    def request(self, career: str, action: str, payload: dict, revision: int) -> bytes:
        self.n += 1
        body = json.dumps(dict(request_id=f"bench-{os.getpid()}-{self.n:08d}", expected_revision=revision,
                               career=career, action=action, payload=payload), ensure_ascii=False).encode()
        head = ("POST /api/command HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\nAccept-Encoding: gzip, deflate, br\r\n"
                f"Cookie: {server.COOKIE}={self.token}\r\nX-Game-CSRF: {self.csrf}\r\n"
                "Origin: http://127.0.0.1\r\nSec-Fetch-Site: same-origin\r\nConnection: close\r\n\r\n").encode()
        return head + body

    def run(self, raw_request: bytes) -> bytes:
        a, b = socket.socketpair()
        try:
            a.sendall(raw_request)
            a.shutdown(socket.SHUT_WR)
            server.Handler(b, ("127.0.0.1", 50000), self.srv)
            b.close()
            chunks = []
            while True:
                data = a.recv(1 << 20)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks)
        finally:
            a.close()
            b.close()


def check(response: bytes, action: str) -> None:
    status = response.split(b"\r\n", 1)[0]
    if b" 200 " not in status:
        head, _, body = response.partition(b"\r\n\r\n")
        if b"Content-Encoding: gzip" in head:
            import gzip
            body = gzip.decompress(body)
        raise SystemExit(f"{action}: {status.decode()} {body[:300].decode(errors='replace')}")


CLOCK: list = []


def measure(bench: Bench, text: str, career: str, action: str, payload: dict, iters: int, profile: cProfile.Profile | None = None):
    revision = 1  # the command stores revision 2: a scoped (not periodic full) validation
    bench.put(text, revision)
    check(bench.run(bench.request(career, action, payload, revision)), action)  # warm-up + sanity check
    cpu, wall, size = [], [], 0
    clock = CLOCK[0]
    for _ in range(iters):
        bench.put(text, revision)
        req = bench.request(career, action, payload, revision)
        if profile:
            profile.enable()
        c0, w0 = clock(), time.perf_counter()
        resp = bench.run(req)
        c1, w1 = clock(), time.perf_counter()
        if profile:
            profile.disable()
        check(resp, action)
        cpu.append((c1 - c0) * 1000)
        wall.append((w1 - w0) * 1000)
        size = len(resp)
    return statistics.median(cpu), wall, size


def _cpu_clock():
    """A precise CPU clock of this thread in seconds: time.thread_time (Linux, macOS), or on
    Windows (where process_time/thread_time tick every 15.6 ms) the thread's cycle counter,
    calibrated against perf_counter while busy."""
    if sys.platform != "win32":
        return time.thread_time
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.GetCurrentThread.restype = ctypes.c_void_p
    k32.QueryThreadCycleTime.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulonglong)]
    handle = k32.GetCurrentThread()
    value = ctypes.c_ulonglong()

    def cycles() -> int:
        k32.QueryThreadCycleTime(handle, ctypes.byref(value))
        return value.value
    c0, t0 = cycles(), time.perf_counter()
    while time.perf_counter() - t0 < 0.3:
        pass
    rate = (cycles() - c0) / (time.perf_counter() - t0)
    return lambda: cycles() / rate


def pin(cpu: int) -> None:
    """Run on one logical CPU (hybrid P/E-core machines otherwise give 2x noise)."""
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {cpu})
    elif sys.platform == "win32":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(), 1 << cpu):
            raise SystemExit(f"could not pin to CPU {cpu}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="100,300,1000", help="save sizes in KB (comma list)")
    ap.add_argument("--actions", default=",".join(ACTIONS), help="benchmark actions (comma list)")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--profile", default="", help="SIZE:ACTION to profile with cProfile (e.g. 300:gr_scan), or 'all'")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--json", default="", help="write the results to this JSON file")
    ap.add_argument("--cpu", type=int, default=-1, help="pin the process to this logical CPU")
    ap.add_argument("--recheck", type=float, default=1e9,
                    help="seconds between static-asset re-checks (default: never, so the numbers do not depend on "
                         "how long each command waits; the cost of one re-check is printed separately)")
    args = ap.parse_args()
    webassets.RECHECK = args.recheck
    if args.cpu >= 0:
        pin(args.cpu)
    CLOCK.append(_cpu_clock())
    sizes = [int(x) for x in args.sizes.split(",") if x]
    actions = [x for x in args.actions.split(",") if x]
    print(f"python {sys.version.split()[0]} · db={'postgresql' if os.environ.get('DATABASE_URL') else 'sqlite'} · "
          f"orjson={'yes' if getattr(fastjson, 'orjson', None) else 'no'} · iters={args.iters}")
    results = []
    with tempfile.TemporaryDirectory() as folder:
        bench = Bench(folder)
        assets = bench.srv.assets
        assets.snapshot()
        costs = []
        for _ in range(5):
            c0 = CLOCK[0]()
            assets._signature()
            costs.append((CLOCK[0]() - c0) * 1000)
        print(f"static-asset re-check (webassets._signature, every RECHECK s per worker): {statistics.median(costs):.2f} ms CPU")
        try:
            for kb in sizes:
                base = grow(kb)
                for action in actions:
                    career = ACTIONS[action]
                    state, payload = prepare(base, action)
                    text = stamped_text(state)
                    want = args.profile in ("all", f"{kb}:{action}")
                    prof = cProfile.Profile() if want else None
                    cpu, wall, size = measure(bench, text, career, action, payload, args.iters, prof)
                    row = dict(size=kb, save_kb=round(len(text.encode()) / 1024), action=action, cpu_ms=round(cpu, 2),
                               wall_ms=round(statistics.median(wall), 2), response_bytes=size)
                    results.append(row)
                    print(f"save {row['save_kb']:5d} KB  {action:11s} cpu {row['cpu_ms']:7.2f} ms  "
                          f"wall(median) {row['wall_ms']:7.2f} ms  response {size} B", flush=True)
                    if prof:
                        out = io.StringIO()
                        st = pstats.Stats(prof, stream=out).sort_stats("tottime")
                        st.print_stats(args.top)
                        print(out.getvalue())
                        out = io.StringIO()
                        pstats.Stats(prof, stream=out).sort_stats("cumulative").print_stats(args.top)
                        print(out.getvalue())
        finally:
            bench.close()
    by_size: dict = {}
    for r in results:
        by_size.setdefault(r["size"], []).append(r["cpu_ms"])
    for kb, xs in by_size.items():
        print(f"~{kb:4d} KB saves: mean cpu {statistics.fmean(xs):.2f} ms per command")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
