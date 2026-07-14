"""Optional CUDA capability and benchmark hooks for the HUNL terminal evaluator."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class GpuStatus:
    available: bool
    device_name: str | None
    total_memory_mb: int | None
    reason: str | None = None


def probe_gpu() -> GpuStatus:
    try:
        import torch
    except ImportError:
        return GpuStatus(False, None, None, "PyTorch with CUDA support is not installed.")
    if not torch.cuda.is_available():
        return GpuStatus(False, None, None, "CUDA is not available to PyTorch.")
    properties = torch.cuda.get_device_properties(0)
    return GpuStatus(True, properties.name, properties.total_memory // (1024 * 1024))


def synthetic_cuda_benchmark(batch_size: int = 1_000_000) -> Dict[str, Any]:
    """Sanity-check CUDA visibility only; this is not a poker-evaluator benchmark."""
    status = probe_gpu()
    if not status.available:
        return {**asdict(status), "benchmark": "unavailable"}
    import torch

    left = torch.rand((batch_size, 7), device="cuda")
    right = torch.rand((batch_size, 7), device="cuda")
    torch.cuda.synchronize()
    started = torch.cuda.Event(enable_timing=True)
    finished = torch.cuda.Event(enable_timing=True)
    started.record()
    _ = (left * right).sum(dim=1)
    finished.record()
    torch.cuda.synchronize()
    return {
        **asdict(status),
        "benchmark": "synthetic_cuda_tensor_only",
        "batch_size": batch_size,
        "elapsed_ms": started.elapsed_time(finished),
        "warning": "Do not treat this as poker solver acceleration.",
    }


def terminal_evaluator_benchmark(batch_size: int = 10_000) -> Dict[str, Any]:
    """Benchmark the actual seven-card evaluator on legal, distinct card batches."""
    status = probe_gpu()
    if not status.available:
        return {**asdict(status), "benchmark": "unavailable"}
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")

    import torch

    from .torch_evaluator import evaluate_seven

    deck = torch.cartesian_prod(
        torch.arange(2, 15, device="cuda", dtype=torch.long),
        torch.arange(4, device="cuda", dtype=torch.long),
    )
    random_keys = torch.rand((batch_size, 52), device="cuda")
    selection = random_keys.argsort(dim=1)[:, :7]
    cards = deck[selection]
    # Warm-up keeps JIT/runtime initialization out of the recorded duration.
    evaluate_seven(cards[: min(batch_size, 256)])
    torch.cuda.synchronize()
    started = torch.cuda.Event(enable_timing=True)
    finished = torch.cuda.Event(enable_timing=True)
    started.record()
    scores = evaluate_seven(cards)
    finished.record()
    torch.cuda.synchronize()
    elapsed_ms = started.elapsed_time(finished)
    if scores.shape != (batch_size,):
        raise RuntimeError("Terminal evaluator returned an unexpected score shape.")
    return {
        **asdict(status),
        "benchmark": "batched_seven_card_terminal_evaluator",
        "batch_size": batch_size,
        "elapsed_ms": elapsed_ms,
        "hands_per_second": batch_size / (elapsed_ms / 1_000) if elapsed_ms else None,
    }
