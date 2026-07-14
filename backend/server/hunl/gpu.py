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
