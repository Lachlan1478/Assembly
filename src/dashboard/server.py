"""
Assembly Dashboard — FastAPI server.

Endpoints:
  GET  /                          Serve index.html
  POST /api/run                   Validate params, start assembly run, return session_id
  WS   /ws/{session_id}           Stream events from asyncio.Queue to browser
  GET  /api/sessions              List past sessions from conversation_logs/
  GET  /api/sessions/{id}         Return stored session JSON for replay

  GET  /api/benchmarks            List all benchmark definitions + latest saved results
  GET  /api/benchmarks/{id}/results  Return latest saved results for one benchmark
  POST /api/benchmarks/{id}/run   Start a benchmark run, return job_id
  WS   /ws/benchmarks/{job_id}    Stream benchmark log lines + completion event

Run with:
  python -m uvicorn src.dashboard.server:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import secrets
import time
import traceback
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.idea_generation.config import MODE_CONFIGS
from src.idea_generation.generator import multiple_llm_idea_generator
from src.dashboard.event_emitter import DashboardEventEmitter, DashboardLogger
from src.dashboard.benchmarks_runner import (
    BENCHMARKS, get_benchmark_results, run_benchmark,
)

# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

class AuthMiddleware:
    """
    ASGI middleware enforcing HTTP Basic Auth on all HTTP and WebSocket routes.

    Skipped entirely when DASHBOARD_PASS is not set (local dev).

    Flow:
    - First request: browser prompts for credentials via WWW-Authenticate: Basic.
    - On valid credentials a session cookie is issued (HttpOnly, 24 h).
    - Subsequent requests (including WebSocket upgrades) present the cookie —
      no re-prompt needed. Browsers attach cookies to WS upgrade requests
      automatically, so WebSocket auth requires no extra client-side code.
    """

    def __init__(self, app):
        self._app = app
        self._user = os.getenv("DASHBOARD_USER", "admin")
        self._pass = os.getenv("DASHBOARD_PASS", "")
        self._sessions: set = set()

    def _check_cookie(self, headers: list) -> bool:
        for name, value in headers:
            if name == b"cookie":
                try:
                    cookie: SimpleCookie = SimpleCookie(value.decode())
                    token = cookie.get("assembly_session")
                    if token and token.value in self._sessions:
                        return True
                except Exception:
                    pass
        return False

    def _validate_basic(self, headers: list) -> "str | None":
        """Return a new session token if Basic credentials are valid, else None."""
        for name, value in headers:
            if name == b"authorization":
                auth = value.decode()
                if auth.startswith("Basic "):
                    try:
                        decoded = b64decode(auth[6:]).decode()
                        username, password = decoded.split(":", 1)
                        user_ok = secrets.compare_digest(username, self._user)
                        pass_ok = secrets.compare_digest(password, self._pass)
                        if user_ok and pass_ok:
                            token = secrets.token_hex(32)
                            self._sessions.add(token)
                            return token
                    except Exception:
                        pass
        return None

    async def __call__(self, scope, receive, send):
        # Auth disabled — local dev
        if not self._pass:
            await self._app(scope, receive, send)
            return

        kind = scope.get("type")
        if kind not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        # Allow health check through without auth
        if scope.get("path") == "/health":
            await self._app(scope, receive, send)
            return

        headers = scope.get("headers", [])

        # Cookie fast-path (covers WebSocket upgrades too)
        if self._check_cookie(headers):
            await self._app(scope, receive, send)
            return

        # Basic Auth
        token = self._validate_basic(headers)
        if token:
            if kind == "websocket":
                # Rarely hit — browser would normally have the cookie already
                await self._app(scope, receive, send)
                return

            # HTTP: inject Set-Cookie into the response
            cookie_value = (
                f"assembly_session={token}; HttpOnly; SameSite=Lax; "
                "Max-Age=86400; Path=/"
            )

            async def send_with_cookie(message):
                if message["type"] == "http.response.start":
                    hdrs = list(message.get("headers", []))
                    hdrs.append((b"set-cookie", cookie_value.encode()))
                    message = {**message, "headers": hdrs}
                await send(message)

            await self._app(scope, receive, send_with_cookie)
            return

        # --- Unauthorized ---
        if kind == "http":
            body = b"Unauthorized"
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"www-authenticate", b'Basic realm="Assembly Dashboard"'),
                    (b"content-type", b"text/plain"),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
        else:
            # WebSocket: consume the connect handshake then close
            await receive()
            await send({"type": "websocket.close", "code": 4401})


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Assembly Dashboard")
app.add_middleware(AuthMiddleware)

STATIC_DIR = Path(__file__).parent / "static"
LOGS_DIR = Path("conversation_logs")

# Per-session state: {session_id: {queue, status, params, result, error}}
sessions: Dict[str, Dict[str, Any]] = {}

# Per-benchmark-job state: {job_id: {queue, status, benchmark_id, result, error}}
benchmark_jobs: Dict[str, Dict[str, Any]] = {}

# Thread pool for running the (blocking) generator and benchmarks
_executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RunParams(BaseModel):
    inspiration: str = Field(..., min_length=10)
    mode: str = "medium"
    number_of_ideas: int = Field(1, ge=1, le=5)
    domain: str = "product"  # "product" | "technical" | "general"
    # The remaining fields are informational (stored) but mode controls the
    # actual config.  We include them so the UI can send overrides if needed.
    max_turns_per_phase: Optional[int] = None
    personas_per_phase: Optional[int] = None
    enable_mediator: Optional[bool] = None
    enable_convergence: Optional[bool] = None
    memory_mode: Optional[str] = None
    model: Optional[str] = None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.get("/")
async def serve_index():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return JSONResponse({"error": "index.html not found"}, status_code=404)
    return FileResponse(str(index), media_type="text/html")


@app.post("/api/run")
async def api_run(params: RunParams):
    if params.mode not in MODE_CONFIGS:
        return JSONResponse(
            {"error": f"Unknown mode '{params.mode}'. Valid: {list(MODE_CONFIGS.keys())}"},
            status_code=400,
        )
    if params.domain not in ("product", "technical", "general"):
        return JSONResponse(
            {"error": f"Unknown domain '{params.domain}'. Valid: product, technical, general"},
            status_code=400,
        )

    session_id = str(uuid4())
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    sessions[session_id] = {
        "queue": queue,
        "status": "starting",
        "params": params.model_dump(),
        "start_time": time.time(),
        "result": None,
        "error": None,
    }

    # Kick off the generator in a background task
    asyncio.create_task(_run_assembly(session_id, params, loop, queue))

    return JSONResponse({"session_id": session_id})


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await ws.accept()

    if session_id not in sessions:
        await ws.send_json({"type": "run_error", "message": "Unknown session"})
        await ws.close()
        return

    session = sessions[session_id]
    queue: asyncio.Queue = session["queue"]

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                # Send a heartbeat so the connection stays alive
                await ws.send_json({"type": "heartbeat"})
                continue

            await ws.send_json(event)
            queue.task_done()

            # Terminal events — close after forwarding
            if event["type"] in ("run_complete", "run_error"):
                break

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@app.get("/api/sessions")
async def list_sessions():
    """List all past sessions from conversation_logs/."""
    if not LOGS_DIR.exists():
        return JSONResponse([])

    sessions_list = []
    for session_dir in sorted(LOGS_DIR.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue
        meta_file = session_dir / "metadata" / "session_metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)
                sessions_list.append({
                    "id": session_dir.name,
                    "timestamp": meta.get("timestamp"),
                    "inspiration": str(meta.get("inspiration", ""))[:80],
                    "mode": meta.get("mode"),
                    "model": meta.get("model"),
                })
            except Exception:
                pass

    return JSONResponse(sessions_list)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Return stored session data for replay."""
    session_dir = LOGS_DIR / session_id
    if not session_dir.exists():
        return JSONResponse({"error": "Session not found"}, status_code=404)

    result: Dict[str, Any] = {}

    meta_file = session_dir / "metadata" / "session_metadata.json"
    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as f:
            result["metadata"] = json.load(f)

    conv_file = session_dir / "metadata" / "full_conversation.json"
    if conv_file.exists():
        with open(conv_file, encoding="utf-8") as f:
            result["exchanges"] = json.load(f)

    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Benchmark routes
# ---------------------------------------------------------------------------

@app.get("/api/benchmarks")
async def list_benchmarks():
    """Return all benchmark definitions plus each one's latest saved results."""
    out = []
    for bm in BENCHMARKS:
        entry = {k: v for k, v in bm.items()}
        entry["latest_results"] = get_benchmark_results(bm["id"])
        out.append(entry)
    return JSONResponse(out)


@app.get("/api/benchmarks/{benchmark_id}/results")
async def get_benchmark_results_endpoint(benchmark_id: str):
    results = get_benchmark_results(benchmark_id)
    if results is None:
        return JSONResponse({"error": "No results found"}, status_code=404)
    return JSONResponse(results)


class BenchmarkRunParams(BaseModel):
    params: Dict[str, Any] = {}


@app.post("/api/benchmarks/{benchmark_id}/run")
async def run_benchmark_endpoint(benchmark_id: str, body: BenchmarkRunParams):
    if not any(b["id"] == benchmark_id for b in BENCHMARKS):
        return JSONResponse({"error": f"Unknown benchmark '{benchmark_id}'"}, status_code=400)

    job_id = str(uuid4())
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)

    benchmark_jobs[job_id] = {
        "queue": queue,
        "status": "starting",
        "benchmark_id": benchmark_id,
        "start_time": time.time(),
        "result": None,
        "error": None,
    }

    asyncio.create_task(_run_benchmark_task(job_id, benchmark_id, body.params, loop, queue))
    return JSONResponse({"job_id": job_id})


@app.websocket("/ws/benchmarks/{job_id}")
async def benchmark_ws(ws: WebSocket, job_id: str):
    await ws.accept()

    if job_id not in benchmark_jobs:
        await ws.send_json({"type": "benchmark_error", "message": "Unknown job"})
        await ws.close()
        return

    queue: asyncio.Queue = benchmark_jobs[job_id]["queue"]

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "heartbeat"})
                continue

            await ws.send_json(event)
            queue.task_done()

            if event["type"] in ("benchmark_complete", "benchmark_error"):
                break

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


async def _run_benchmark_task(
    job_id: str,
    benchmark_id: str,
    params: Dict[str, Any],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    job = benchmark_jobs[job_id]
    job["status"] = "running"

    queue.put_nowait({"type": "benchmark_started", "job_id": job_id, "benchmark_id": benchmark_id, "ts": time.time()})

    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: run_benchmark(benchmark_id, queue, loop, params),
        )
        job["status"] = "complete"
        job["result"] = result
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        queue.put_nowait({
            "type": "benchmark_error",
            "message": str(exc),
            "detail": traceback.format_exc(),
            "ts": time.time(),
        })


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------

async def _run_assembly(
    session_id: str,
    params: RunParams,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    """Run the assembly generator in a thread pool and stream events via queue."""
    session = sessions[session_id]
    session["status"] = "running"

    # Build per-session emitter and logger
    emitter = DashboardEventEmitter(queue=queue, loop=loop)
    dash_logger = DashboardLogger(queue=queue, loop=loop, base_dir="conversation_logs")

    # Announce the run (we're in the FastAPI event loop here, so direct put is fine)
    queue.put_nowait({
        "type": "run_started",
        "session_id": session_id,
        "params": params.model_dump(),
        "ts": time.time(),
    })

    # Build overrides dict from any non-None UI params
    overrides = {}
    if params.max_turns_per_phase is not None:
        overrides["max_turns_per_phase"] = params.max_turns_per_phase
    if params.personas_per_phase is not None:
        overrides["personas_per_phase"] = params.personas_per_phase
    if params.enable_mediator is not None:
        overrides["enable_mediator"] = params.enable_mediator
    if params.enable_convergence is not None:
        overrides["enable_convergence_phase"] = params.enable_convergence
    if params.memory_mode is not None:
        overrides["memory_mode"] = params.memory_mode
    if params.model is not None:
        overrides["model"] = params.model

    try:
        # Run the blocking generator in a thread so the FastAPI event loop
        # stays free.  asyncio.run() inside the thread creates its own event
        # loop — the emitter uses call_soon_threadsafe to bridge back.
        result = await loop.run_in_executor(
            _executor,
            lambda: multiple_llm_idea_generator(
                inspiration=params.inspiration,
                number_of_ideas=params.number_of_ideas,
                mode=params.mode,
                domain=params.domain,
                monitor=emitter,
                logger=dash_logger,
                config_overrides=overrides or None,
            ),
        )

        session["status"] = "complete"
        session["result"] = result

        # Back in the FastAPI event loop after await — direct put is fine
        queue.put_nowait({
            "type": "run_complete",
            "ideas": result if isinstance(result, list) else result.get("ideas", []),
            "convergence": result.get("convergence") if isinstance(result, dict) else None,
            "total_time": time.time() - session["start_time"],
            "ts": time.time(),
        })

    except Exception as exc:
        session["status"] = "error"
        session["error"] = str(exc)

        queue.put_nowait({
            "type": "run_error",
            "message": str(exc),
            "detail": traceback.format_exc(),
            "ts": time.time(),
        })
