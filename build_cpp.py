"""Build helper for the mock C++ backend.

This mirrors a production-style helper that configures CMake and resolves the
xcp_backend executable, but the backend itself is synthetic and public-safe.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CPP_ROOT = ROOT / "_backend" / "cpp"


def get_exe_path() -> Path:
    names = ["xcp_backend.exe", "xcp_backend"]
    candidates = [
        CPP_ROOT / "build" / "Release" / n for n in names
    ] + [
        CPP_ROOT / "build" / n for n in names
    ]
    for path in candidates:
        if path.exists():
            return path
    return CPP_ROOT / "build" / ("xcp_backend.exe" if __import__('os').name == 'nt' else "xcp_backend")


def build(release: bool = True) -> Path:
    cmake = shutil.which("cmake")
    if not cmake:
        raise RuntimeError("CMake was not found on PATH.")
    build_dir = CPP_ROOT / "build"
    config = "Release" if release else "Debug"
    subprocess.check_call([cmake, "-S", str(CPP_ROOT), "-B", str(build_dir), f"-DCMAKE_BUILD_TYPE={config}"])
    subprocess.check_call([cmake, "--build", str(build_dir), "--config", config])
    return get_exe_path()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Build Debug instead of Release")
    parser.add_argument("--release", action="store_true", help="Build Release; default")
    args = parser.parse_args()
    exe = build(release=not args.debug)
    print(exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
