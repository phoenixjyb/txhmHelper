from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from solver_cfr import solve_cfr
import traceback

app = FastAPI(title="TX Hold'em GTO API", version="0.1.0")


class SolvePayload(BaseModel):
    stage: str = Field(pattern="(?i)preflop|flop|turn|river")
    hole: List[str] = Field(..., min_length=2, max_length=2, description="Player hole cards like ['As','Kd']")
    board: List[str] = Field(default_factory=list, max_length=5, description="Board cards like ['Jh','Td','2c']")
    pot: float = Field(..., gt=0)
    effective_stack: float = Field(..., gt=0)
    bet_sizing: List[float] = Field(default_factory=lambda: [0.33, 0.5, 1.0], description="Pot fraction sizes available for betting/raising")


class SolveResponse(BaseModel):
    strategy: Dict[str, float]
    note: str = "Strategy from simplified CFR solver (single bet size, no raises)."


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve", response_model=SolveResponse)
def post_solve(payload: SolvePayload):
    try:
        bet_frac = payload.bet_sizing[0] if payload.bet_sizing else 1.0
        strategy = solve_cfr(
            stage=payload.stage,
            hole=payload.hole,
            board=payload.board,
            pot=payload.pot,
            effective_stack=payload.effective_stack,
            bet_frac=bet_frac,
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
    return SolveResponse(strategy=strategy)


# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
