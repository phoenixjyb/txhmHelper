"""Planning and report helpers for sequential held-out Gate B stability jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence

from .gate_b_validation import HeldOutFlopCase


@dataclass(frozen=True)
class HeldOutBatchJob:
    case: HeldOutFlopCase
    seed: int
    output_dir: Path

    @property
    def label(self) -> str:
        return f"{self.case.case_id}-seed{self.seed}"

    @property
    def exact_artifact(self) -> Path:
        return self.output_dir / f"{self.label}-exact.json"

    @property
    def bucketed_artifact(self) -> Path:
        return self.output_dir / f"{self.label}-bucketed.json"

    @property
    def report(self) -> Path:
        return self.output_dir / f"{self.label}-report.json"

    @property
    def log(self) -> Path:
        return self.output_dir / f"{self.label}.log"


def build_held_out_jobs(
    cases: Iterable[HeldOutFlopCase], seeds: Sequence[int], output_dir: str | Path
) -> list[HeldOutBatchJob]:
    if not seeds:
        raise ValueError("At least one seed is required for a held-out batch.")
    return [HeldOutBatchJob(case, seed, Path(output_dir)) for case in cases for seed in seeds]


def stable_report_summary(path: Path) -> Dict[str, object] | None:
    """Return a concise stable report payload, or None for absent/unstable reports."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("stable"):
        return None
    history = payload.get("history", [])
    if not history:
        raise ValueError(f"Stable report {path} has no checkpoint history.")
    return {
        "total_iterations": history[-1]["total_iterations"],
        "last_checkpoint": history[-1],
        "checkpoint_count": len(history),
    }


def write_json_atomic(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
