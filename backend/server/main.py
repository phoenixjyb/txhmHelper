from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from threading import RLock
import traceback
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from solver_cfr import solve_cfr
from solver_v2 import HeadsUpPostflopCfr, WeightedCombo

app = FastAPI(title="TX Hold'em GTO API", version="0.2.0")


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


class V1SolveResult(BaseModel):
    strategy: Dict[str, float]
    iterations: int
    node_count: int
    model: str
    note: str


class SolveJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "complete", "failed"]
    cache_hit: bool = False
    result: Optional[V1SolveResult] = None
    error: Optional[str] = None


@dataclass
class SolveJob:
    status: Literal["queued", "running", "complete", "failed"]
    result: Optional[V1SolveResult] = None
    error: Optional[str] = None


jobs: Dict[str, SolveJob] = {}
cache: Dict[str, str] = {}
jobs_lock = RLock()
solver_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="txhm-cfr")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "solver": "heads-up-postflop-cfr-plus-v1",
        "gpu_accelerated": "false",
    }


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
    cache_key = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    with jobs_lock:
        existing_job_id = cache.get(cache_key)
        if existing_job_id:
            return _job_response(existing_job_id, cache_hit=True)

        job_id = str(uuid4())
        jobs[job_id] = SolveJob(status="queued")
        cache[cache_key] = job_id
        solver_executor.submit(_run_v1_solve, job_id, payload)
        return _job_response(job_id)


@app.get("/v1/solve/{job_id}", response_model=SolveJobResponse)
def get_v1_solve(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Unknown solve job.")
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
        jobs[job_id].status = "running"
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
        )
        result = V1SolveResult(
            strategy=solved.strategy,
            iterations=solved.iterations,
            node_count=solved.node_count,
            model=solved.model,
            note=(
                "CFR+ in a bounded heads-up postflop game: weighted villain range, "
                "configured bet sizes, one capped raise, and sampled runouts. "
                "Later-street decisions are not yet modeled."
            ),
        )
        with jobs_lock:
            jobs[job_id] = SolveJob(status="complete", result=result)
    except Exception as exc:
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id] = SolveJob(status="failed", error=str(exc))


def _job_response(job_id: str, cache_hit: bool = False) -> SolveJobResponse:
    job = jobs[job_id]
    return SolveJobResponse(
        job_id=job_id,
        status=job.status,
        cache_hit=cache_hit,
        result=job.result,
        error=job.error,
    )
