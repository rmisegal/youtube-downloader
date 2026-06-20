"""GPU detection + CUDA-libs enablement (shared with transcribe-video, IN PLACE).

The default beat/structure DSP (``librosa``) is CPU-only and already meets the
<10s NFR, so the default device is CPU. GPU acceleration applies to an OPTIONAL
neural backend (onnxruntime/torch beat models): when one is installed it loads
the CUDA/cuDNN DLLs from the transcribe-video project — referenced IN PLACE,
never copied — exactly as ``transcribe-video/transcribe.py`` does.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Shared CUDA 12 / cuDNN 9 DLLs from the transcribe-video project (not copied).
CUDA_LIBS = Path(r"C:\25D\GeneralLearning\transcribe-video\cuda_libs")
_OFF = frozenset({"off", "false", "no", "0", "cpu", "none", ""})


def enable_cuda_libs(cuda_libs: Path = CUDA_LIBS) -> bool:
    """Prepend the shared cuda_libs dir to PATH (in place) so a GPU lib can load
    the CUDA/cuDNN DLLs. Returns ``True`` when the dir exists. Idempotent."""
    if not cuda_libs.is_dir():
        return False
    current = os.environ.get("PATH", "")
    if str(cuda_libs) not in current:
        os.environ["PATH"] = str(cuda_libs) + os.pathsep + current
    adder = getattr(os, "add_dll_directory", None)
    if callable(adder):
        with contextlib.suppress(OSError):
            adder(str(cuda_libs))
    return True


def has_nvidia_gpu(runner: Callable[..., Any] = subprocess.run) -> bool:
    """True when an NVIDIA GPU is visible (``nvidia-smi -L`` lists one)."""
    if not shutil.which("nvidia-smi"):
        return False
    try:
        result = runner(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return getattr(result, "returncode", 1) == 0 and "GPU" in (getattr(result, "stdout", "") or "")


def resolve_device(
    use_gpu: str = "auto",
    *,
    runner: Callable[..., Any] = subprocess.run,
    cuda_libs: Path = CUDA_LIBS,
) -> str:
    """Resolve ``analysis.use_gpu`` to ``"gpu"`` or ``"cpu"``.

    ``off``/``false`` → cpu. ``auto``/``on`` → gpu only when an NVIDIA GPU AND the
    shared cuda_libs are both available (then the libs are put on PATH); else cpu.
    """
    if str(use_gpu).strip().lower() in _OFF:
        return "cpu"
    if not has_nvidia_gpu(runner):
        return "cpu"
    if not enable_cuda_libs(cuda_libs):
        return "cpu"
    return "gpu"
