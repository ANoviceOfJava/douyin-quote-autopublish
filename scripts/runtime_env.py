"""Create and validate the private runtime for douyin-quote-autopublish."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 10)
REQUIRED_MODULES = (
    "cv2",
    "imageio_ffmpeg",
    "PIL",
    "rapidocr_onnxruntime",
    "yt_dlp",
)
SKILL_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_PATH = SKILL_ROOT / "requirements.txt"


def get_runtime_root() -> Path:
    """Return the writable directory used for the private virtual environment."""
    override = os.environ.get("DOUYIN_SKILL_VENV")
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return (base / "cache" / "douyin-quote-autopublish" / "venv").resolve()


def get_venv_python(runtime_root: Path | None = None) -> Path:
    """Return the platform-specific Python path inside the private runtime."""
    root = runtime_root or get_runtime_root()
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def requirements_sha256() -> str:
    """Hash the dependency manifest so changes trigger a runtime refresh."""
    if not REQUIREMENTS_PATH.is_file():
        raise RuntimeError(f"requirements file does not exist: {REQUIREMENTS_PATH}")
    return hashlib.sha256(REQUIREMENTS_PATH.read_bytes()).hexdigest()


def read_marker(runtime_root: Path) -> dict[str, Any] | None:
    marker = runtime_root / ".runtime-ready.json"
    if not marker.is_file():
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def probe_modules(python_path: Path) -> dict[str, bool]:
    """Check importability without loading the heavy OCR and video libraries."""
    probe = (
        "import importlib.util,json;"
        f"mods={list(REQUIRED_MODULES)!r};"
        "print(json.dumps({name: importlib.util.find_spec(name) is not None for name in mods}))"
    )
    result = subprocess.run(
        [str(python_path), "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return {name: False for name in REQUIRED_MODULES}
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {name: False for name in REQUIRED_MODULES}
    return {name: bool(value.get(name)) for name in REQUIRED_MODULES}


def status() -> dict[str, Any]:
    """Return the current private-runtime status without changing files."""
    runtime_root = get_runtime_root()
    python_path = get_venv_python(runtime_root)
    values = {
        "runtime_root": str(runtime_root),
        "python_path": str(python_path),
        "requirements": str(REQUIREMENTS_PATH),
        "requirements_sha256": requirements_sha256(),
        "modules": {name: False for name in REQUIRED_MODULES},
        "ready": False,
    }
    if not python_path.is_file():
        return values
    marker = read_marker(runtime_root)
    if not marker or marker.get("requirements_sha256") != values["requirements_sha256"]:
        return values
    modules = probe_modules(python_path)
    values["modules"] = modules
    values["ready"] = all(modules.values())
    return values


def ensure_environment(auto_install: bool = True) -> dict[str, Any]:
    """Ensure the private runtime exists and contains all required packages."""
    if sys.version_info < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"current version is {sys.version.split()[0]}"
        )

    current = status()
    if current["ready"]:
        return current
    if not auto_install:
        return current

    runtime_root = get_runtime_root()
    python_path = get_venv_python(runtime_root)
    print(f"[skill] preparing private runtime: {runtime_root}", file=sys.stderr)
    if not python_path.is_file():
        runtime_root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(runtime_root)], check=True)

    pip_check = subprocess.run(
        [str(python_path), "-m", "pip", "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if pip_check.returncode != 0:
        subprocess.run([str(python_path), "-m", "ensurepip", "--upgrade"], check=True)

    print("[skill] installing pinned runtime dependencies", file=sys.stderr)
    subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(REQUIREMENTS_PATH),
        ],
        check=True,
    )

    modules = probe_modules(python_path)
    if not all(modules.values()):
        missing = ", ".join(name for name, present in modules.items() if not present)
        raise RuntimeError(f"runtime installation finished but modules are missing: {missing}")

    marker = {
        "requirements_sha256": requirements_sha256(),
        "python_version": sys.version.split()[0],
        "modules": list(REQUIRED_MODULES),
    }
    (runtime_root / ".runtime-ready.json").write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("[skill] private runtime is ready", file=sys.stderr)
    return status()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check without installing")
    parser.add_argument("--install", action="store_true", help="create or refresh the private runtime")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    if args.check and args.install:
        parser.error("--check and --install cannot be used together")
    if args.check:
        result = status()
    else:
        result = ensure_environment(auto_install=True)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("ready" if result["ready"] else "not ready")
    raise SystemExit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
