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
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
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
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Assembly Dashboard")

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
