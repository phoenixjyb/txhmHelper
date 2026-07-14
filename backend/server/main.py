from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from threading import RLock
import time
import traceback
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from solver_cfr import solve_cfr
from solver_v2 import HeadsUpPostflopCfr, WeightedCombo
from hunl.gpu import probe_gpu
from table_context import TableAction, normalize_table_context

app = FastAPI(title="TX Hold'em GTO API", version="0.5.0")

RESULT_CACHE_LIMIT = max(1, int(os.getenv("TXHM_RESULT_CACHE_LIMIT", "512")))
JOB_TTL_SECONDS = max(60, int(os.getenv("TXHM_JOB_TTL_SECONDS", "3600")))
RESULT_CACHE_PATH = Path(os.getenv("TXHM_RESULT_CACHE_PATH", "runtime/solve_result_cache.json"))
SOLVER_WORKERS = max(1, int(os.getenv("TXHM_SOLVER_WORKERS", "1")))


class SolvePayload(BaseModel):
    """Compatibility payload used by the current Android application."""

    stage: str = Field(pattern="(?i)preflop|flop|turn|river")
    hole: List[str] = Field(..., min_length=2, max_length=2)
    board: List[str] = Field(default_factory=list, max_length=5)
    pot: float = Field(..., gt=0)
    effective_stack: float = Field(..., gt=0)
    bet_sizing: List[float] = Field(default_factory=lambda: [0.33, 0.5, 1.0])


class SolveResponse(BaseModel):
    strategy: Dict[str, float]
    note: str = "Strategy from chance-sampled CFR in a heads-up, one-street abstraction (no raises)."


class RangeComboPayload(BaseModel):
    cards: List[str] = Field(..., min_length=2, max_length=2)
    weight: float = Field(..., gt=0)


class V1SolvePayload(BaseModel):
    """Bounded heads-up postflop game; Hero must be the next player to act."""

    stage: Literal["flop", "turn", "river"]
    hole: List[str] = Field(..., min_length=2, max_length=2)
    board: List[str] = Field(..., min_length=3, max_length=5)
    pot: float = Field(..., gt=0)
    effective_stack: float = Field(..., gt=0)
    hero_position: Literal["oop", "ip"] = "oop"
    action_history: List[str] = Field(default_factory=list, max_length=4)
    villain_range: Optional[List[RangeComboPayload]] = None
    bet_sizing: List[float] = Field(default_factory=lambda: [0.33, 0.5, 1.0], min_length=1, max_length=4)
    raise_sizing: List[float] = Field(default_factory=lambda: [0.75, 1.5], min_length=1, max_length=3)
    raise_cap: int = Field(default=1, ge=0, le=1)
    rake_pct: float = Field(default=0.0, ge=0, le=0.10)
    rake_cap: float = Field(default=0.0, ge=0)
    iterations: int = Field(default=5_000, ge=100, le=50_000)
    terminal_evaluator: Literal["cpu", "cuda"] = "cpu"


class TableActionPayload(BaseModel):
    """A real-table action recorded by the Android client for one street."""

    player: Literal["hero", "villain"]
    type: Literal["check", "bet", "call", "raise", "fold", "all_in"]
    amount_to: Optional[float] = Field(default=None, gt=0)


class TableSolvePayload(BaseModel):
    """Heads-up table context with exact action amounts on the current street."""

    stage: Literal["flop", "turn", "river"]
    hole: List[str] = Field(..., min_length=2, max_length=2)
    board: List[str] = Field(..., min_length=3, max_length=5)
    pot_before_street: float = Field(..., gt=0)
    effective_stack: float = Field(..., gt=0)
    hero_position: Literal["oop", "ip"] = "oop"
    actions: List[TableActionPayload] = Field(default_factory=list, max_length=4)
    villain_range: Optional[List[RangeComboPayload]] = None
    bet_sizing: List[float] = Field(default_factory=lambda: [0.33, 0.5, 1.0], min_length=1, max_length=8)
    raise_sizing: List[float] = Field(default_factory=lambda: [0.75, 1.5], min_length=1, max_length=8)
    raise_cap: int = Field(default=1, ge=0, le=1)
    rake_pct: float = Field(default=0.0, ge=0, le=0.10)
    rake_cap: float = Field(default=0.0, ge=0)
    iterations: int = Field(default=5_000, ge=100, le=50_000)
    terminal_evaluator: Literal["cpu", "cuda"] = "cpu"


class V1SolveResult(BaseModel):
    strategy: Dict[str, float]
    iterations: int
    node_count: int
    model: str
    terminal_evaluator: str
    action_history: List[str] = Field(default_factory=list)
    note: str


class SolveJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "complete", "failed", "cancelled"]
    cache_hit: bool = False
    result: Optional[V1SolveResult] = None
    error: Optional[str] = None


@dataclass
class SolveJob:
    status: Literal["queued", "running", "complete", "failed", "cancelled"]
    result: Optional[V1SolveResult] = None
    error: Optional[str] = None
    cache_key: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cancel_requested: bool = False


@dataclass
class RuntimeMetrics:
    submitted: int = 0
    in_flight_cache_hits: int = 0
    result_cache_hits: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_solve_seconds: float = 0.0


jobs: Dict[str, SolveJob] = {}
cache: Dict[str, str] = {}
result_cache: OrderedDict[str, V1SolveResult] = OrderedDict()
metrics = RuntimeMetrics()
jobs_lock = RLock()
solver_executor = ThreadPoolExecutor(max_workers=SOLVER_WORKERS, thread_name_prefix="txhm-cfr")


def _load_result_cache() -> None:
    """Restore completed solves so restarts do not discard useful work."""
    try:
        payload = json.loads(RESULT_CACHE_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        for entry in entries[-RESULT_CACHE_LIMIT:]:
            result_cache[entry["key"]] = V1SolveResult.model_validate(entry["result"])
    except FileNotFoundError:
        return
    except (OSError, ValueError, KeyError) as exc:
        print(f"Ignoring unreadable solve-result cache: {exc}")


def _persist_result_cache_locked() -> None:
    """Write the LRU atomically; an unwritable cache must not break solving."""
    try:
        RESULT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = RESULT_CACHE_PATH.with_suffix(RESULT_CACHE_PATH.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "version": 1,
                    "entries": [
                        {"key": key, "result": result.model_dump(mode="json")}
                        for key, result in result_cache.items()
                    ],
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        temporary.replace(RESULT_CACHE_PATH)
    except OSError as exc:
        print(f"Could not persist solve-result cache: {exc}")


def _store_result_locked(cache_key: str, result: V1SolveResult) -> None:
    result_cache[cache_key] = result
    result_cache.move_to_end(cache_key)
    while len(result_cache) > RESULT_CACHE_LIMIT:
        result_cache.popitem(last=False)
    _persist_result_cache_locked()


def _prune_expired_jobs_locked() -> None:
    now = time.monotonic()
    expired_job_ids = [
        job_id
        for job_id, job in jobs.items()
        if job.status in ("complete", "failed", "cancelled")
        and job.completed_at is not None
        and now - job.completed_at > JOB_TTL_SECONDS
    ]
    for job_id in expired_job_ids:
        job = jobs.pop(job_id)
        if job.cache_key and cache.get(job.cache_key) == job_id:
            cache.pop(job.cache_key, None)


def _metrics_snapshot_locked() -> Dict[str, float | int]:
    queued = sum(job.status == "queued" for job in jobs.values())
    running = sum(job.status == "running" for job in jobs.values())
    average_solve_seconds = metrics.total_solve_seconds / metrics.completed if metrics.completed else 0.0
    return {
        "solver_workers": SOLVER_WORKERS,
        "queue_depth": queued,
        "running_jobs": running,
        "tracked_jobs": len(jobs),
        "result_cache_entries": len(result_cache),
        "submitted": metrics.submitted,
        "in_flight_cache_hits": metrics.in_flight_cache_hits,
        "result_cache_hits": metrics.result_cache_hits,
        "completed": metrics.completed,
        "failed": metrics.failed,
        "cancelled": metrics.cancelled,
        "average_solve_seconds": round(average_solve_seconds, 4),
    }


_load_result_cache()


@app.get("/health")
def health():
    gpu = probe_gpu()
    return {
        "status": "ok",
        "version": "0.5.0",
        "solver": "heads-up-postflop-cfr-plus-v1",
        "gpu_terminal_evaluator_available": gpu.available,
        "gpu_device": gpu.device_name,
    }


@app.get("/v1/metrics")
def get_metrics():
    with jobs_lock:
        _prune_expired_jobs_locked()
        return _metrics_snapshot_locked()


@app.post("/solve", response_model=SolveResponse)
def post_solve(payload: SolvePayload):
    """Legacy synchronous endpoint retained for the installed Android client."""
    try:
        strategy = solve_cfr(
            stage=payload.stage,
            hole=payload.hole,
            board=payload.board,
            pot=payload.pot,
            effective_stack=payload.effective_stack,
            bet_sizes=payload.bet_sizing,
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=str(exc))
    return SolveResponse(strategy=strategy)


@app.post("/v1/solve", response_model=SolveJobResponse, status_code=202)
def create_v1_solve(payload: V1SolvePayload):
    _validate_v1_payload(payload)
    return _enqueue_v1_solve(payload)


@app.post("/v1/table/solve", response_model=SolveJobResponse, status_code=202)
def create_table_solve(payload: TableSolvePayload):
    expected_board_cards = {"flop": 3, "turn": 4, "river": 5}
    if len(payload.board) != expected_board_cards[payload.stage]:
        raise HTTPException(
            status_code=422,
            detail=f"{payload.stage} requires {expected_board_cards[payload.stage]} board cards.",
        )
    try:
        normalized = normalize_table_context(
            pot_before_street=payload.pot_before_street,
            effective_stack=payload.effective_stack,
            hero_position=payload.hero_position,
            actions=[TableAction(item.player, item.type, item.amount_to) for item in payload.actions],
            bet_sizing=payload.bet_sizing,
            raise_sizing=payload.raise_sizing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    solver_payload = V1SolvePayload(
        stage=payload.stage,
        hole=payload.hole,
        board=payload.board,
        pot=payload.pot_before_street,
        effective_stack=payload.effective_stack,
        hero_position=payload.hero_position,
        action_history=normalized.action_history,
        villain_range=payload.villain_range,
        bet_sizing=normalized.bet_sizing,
        raise_sizing=normalized.raise_sizing,
        raise_cap=payload.raise_cap,
        rake_pct=payload.rake_pct,
        rake_cap=payload.rake_cap,
        iterations=payload.iterations,
        terminal_evaluator=payload.terminal_evaluator,
    )
    _validate_v1_payload(solver_payload)
    return _enqueue_v1_solve(solver_payload)


def _enqueue_v1_solve(payload: V1SolvePayload) -> SolveJobResponse:
    cache_key = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    with jobs_lock:
        _prune_expired_jobs_locked()
        existing_job_id = cache.get(cache_key)
        if existing_job_id:
            metrics.in_flight_cache_hits += 1
            return _job_response(existing_job_id, cache_hit=True)

        cached_result = result_cache.get(cache_key)
        if cached_result is not None:
            result_cache.move_to_end(cache_key)
            metrics.result_cache_hits += 1
            job_id = str(uuid4())
            now = time.monotonic()
            jobs[job_id] = SolveJob(
                status="complete",
                result=cached_result,
                cache_key=cache_key,
                created_at=now,
                started_at=now,
                completed_at=now,
            )
            cache[cache_key] = job_id
            return _job_response(job_id, cache_hit=True)

        job_id = str(uuid4())
        jobs[job_id] = SolveJob(status="queued", cache_key=cache_key)
        cache[cache_key] = job_id
        metrics.submitted += 1
        solver_executor.submit(_run_v1_solve, job_id, payload)
        return _job_response(job_id)


@app.get("/v1/solve/{job_id}", response_model=SolveJobResponse)
def get_v1_solve(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Unknown solve job.")
        return _job_response(job_id)


@app.delete("/v1/solve/{job_id}", response_model=SolveJobResponse)
def cancel_v1_solve(job_id: str):
    """Stop queued work or suppress a running result that is no longer useful."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Unknown solve job.")
        job = jobs[job_id]
        if job.status in ("complete", "failed", "cancelled"):
            return _job_response(job_id)
        job.cancel_requested = True
        job.status = "cancelled"
        job.completed_at = time.monotonic()
        if job.cache_key and cache.get(job.cache_key) == job_id:
            cache.pop(job.cache_key, None)
        metrics.cancelled += 1
        return _job_response(job_id)


def _validate_v1_payload(payload: V1SolvePayload) -> None:
    expected_board_cards = {"flop": 3, "turn": 4, "river": 5}
    if len(payload.board) != expected_board_cards[payload.stage]:
        raise HTTPException(
            status_code=422,
            detail=f"{payload.stage} requires {expected_board_cards[payload.stage]} board cards.",
        )


def _run_v1_solve(job_id: str, payload: V1SolvePayload) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None or job.cancel_requested:
            return
        job.status = "running"
        job.started_at = time.monotonic()
    try:
        weighted_range = (
            [WeightedCombo(tuple(entry.cards), entry.weight) for entry in payload.villain_range]
            if payload.villain_range
            else None
        )
        solver = HeadsUpPostflopCfr(
            pot=payload.pot,
            effective_stack=payload.effective_stack,
            bet_sizes=payload.bet_sizing,
            raise_sizes=payload.raise_sizing,
            raise_cap=payload.raise_cap,
            rake_pct=payload.rake_pct,
            rake_cap=payload.rake_cap,
        )
        solved = solver.solve(
            hero_hand=payload.hole,
            public_board=payload.board,
            hero_position=payload.hero_position,
            action_history=payload.action_history,
            villain_range=weighted_range,
            iterations=payload.iterations,
            use_gpu_terminal_evaluator=payload.terminal_evaluator == "cuda",
        )
        result = V1SolveResult(
            strategy=solved.strategy,
            iterations=solved.iterations,
            node_count=solved.node_count,
            model=solved.model,
            terminal_evaluator=solved.terminal_evaluator,
            action_history=list(payload.action_history),
            note=(
                "CFR+ in a bounded heads-up postflop game: weighted villain range, "
                "configured bet sizes, one capped raise, and sampled runouts. "
                "Later-street decisions are not yet modeled. "
                f"Terminal payoffs used the {solved.terminal_evaluator} evaluator."
            ),
        )
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None or job.cancel_requested:
                return
            completed_at = time.monotonic()
            job.status = "complete"
            job.result = result
            job.completed_at = completed_at
            metrics.completed += 1
            if job.started_at is not None:
                metrics.total_solve_seconds += completed_at - job.started_at
            if job.cache_key:
                _store_result_locked(job.cache_key, result)
    except Exception as exc:
        traceback.print_exc()
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None or job.cancel_requested:
                return
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = time.monotonic()
            metrics.failed += 1
            if job.cache_key and cache.get(job.cache_key) == job_id:
                cache.pop(job.cache_key, None)


def _job_response(job_id: str, cache_hit: bool = False) -> SolveJobResponse:
    job = jobs[job_id]
    return SolveJobResponse(
        job_id=job_id,
        status=job.status,
        cache_hit=cache_hit,
        result=job.result,
        error=job.error,
    )
