"""Unit tests for GPU detection / cuda_libs enablement (no real GPU/subprocess)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ytdl.services.analysis import gpu


def _smi(found: bool, listed: bool = True):
    def runner(_cmd, **_kw):
        if not found:
            raise FileNotFoundError
        return SimpleNamespace(returncode=0, stdout="GPU 0: NVIDIA" if listed else "")

    return runner


def test_resolve_device_off_is_cpu() -> None:
    assert gpu.resolve_device("off") == "cpu"
    assert gpu.resolve_device("false") == "cpu"


def test_resolve_device_auto_no_gpu_is_cpu(monkeypatch) -> None:
    monkeypatch.setattr(gpu.shutil, "which", lambda _n: None)  # no nvidia-smi
    assert gpu.resolve_device("auto") == "cpu"


def test_resolve_device_auto_gpu_present_enables_cuda_libs(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(gpu.shutil, "which", lambda _n: "nvidia-smi")
    libs = tmp_path / "cuda_libs"
    libs.mkdir()
    monkeypatch.setenv("PATH", "C:/x")
    dev = gpu.resolve_device("auto", runner=_smi(True), cuda_libs=libs)
    assert dev == "gpu"
    assert str(libs) in gpu.os.environ["PATH"]  # libs put on PATH (in place)


def test_resolve_device_gpu_but_no_cuda_libs_is_cpu(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(gpu.shutil, "which", lambda _n: "nvidia-smi")
    missing = tmp_path / "nope"
    assert gpu.resolve_device("auto", runner=_smi(True), cuda_libs=missing) == "cpu"


def test_has_nvidia_gpu_handles_missing_and_error(monkeypatch) -> None:
    monkeypatch.setattr(gpu.shutil, "which", lambda _n: None)
    assert gpu.has_nvidia_gpu() is False
    monkeypatch.setattr(gpu.shutil, "which", lambda _n: "nvidia-smi")
    assert gpu.has_nvidia_gpu(runner=_smi(False)) is False


def test_enable_cuda_libs_missing_dir_returns_false() -> None:
    assert gpu.enable_cuda_libs(Path("Z:/no/such/cuda")) is False
