"""Portable launcher that bootstraps and uses the skill private runtime."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from runtime_env import SKILL_ROOT, ensure_environment, get_venv_python


def run_command(command: Sequence[str]) -> int:
    """Run a command with inherited standard streams and return its exit code."""
    return subprocess.run(list(command), check=False).returncode


def run_script(script_name: str, args: Sequence[str]) -> int:
    """Run one of this skill's Python scripts inside the private runtime."""
    script = (SKILL_ROOT / "scripts" / script_name).resolve()
    if script.parent != (SKILL_ROOT / "scripts").resolve() or not script.is_file():
        raise RuntimeError(f"unknown skill script: {script_name}")
    return run_command([str(get_venv_python()), str(script), *args])


def run_module(module_name: str, args: Sequence[str]) -> int:
    """Run an installed Python module inside the private runtime."""
    return run_command([str(get_venv_python()), "-m", module_name, *args])


def ffmpeg_executable() -> Path:
    """Resolve the ffmpeg binary bundled by imageio-ffmpeg."""
    probe = "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
    result = subprocess.run(
        [str(get_venv_python()), "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = result.stdout.strip().splitlines()[-1]
    path = Path(value)
    if not path.is_file():
        raise RuntimeError(f"ffmpeg binary is unavailable: {path}")
    return path


def print_help() -> None:
    """Print supported launcher commands."""
    print(
        "usage: python scripts/run.py <command> [args...]\n\n"
        "commands:\n"
        "  check [--json]        create/verify the private runtime\n"
        "  state [...]            run scripts/workflow_state.py\n"
        "  ocr [...]              run scripts/ocr_subtitles.py\n"
        "  yt-dlp [...]           run the installed yt-dlp module\n"
        "  ffmpeg [...]           run the bundled imageio-ffmpeg binary\n"
        "  python <script> [...]  run a script with the private Python"
    )


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help", "help"}:
        print_help()
        return

    command = args[0]
    rest = args[1:]
    if command == "check":
        auto_install = "--no-install" not in rest
        result = ensure_environment(auto_install=auto_install)
        if "--json" in rest:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("ready" if result["ready"] else "not ready")
        raise SystemExit(0 if result["ready"] else 1)

    ensure_environment(auto_install=True)

    if command == "state":
        code = run_script("workflow_state.py", rest)
    elif command == "ocr":
        code = run_script("ocr_subtitles.py", rest)
    elif command == "yt-dlp":
        code = run_module("yt_dlp", rest)
    elif command == "ffmpeg":
        code = run_command([str(ffmpeg_executable()), *rest])
    elif command == "python":
        if not rest:
            raise SystemExit("python command requires a script path")
        script = Path(rest[0]).expanduser()
        if not script.is_absolute():
            skill_candidate = (SKILL_ROOT / script).resolve()
            working_candidate = (Path.cwd() / script).resolve()
            script = skill_candidate if skill_candidate.is_file() else working_candidate
        if not script.is_file():
            raise SystemExit(f"python script does not exist: {script}")
        code = run_command([str(get_venv_python()), str(script), *rest[1:]])
    else:
        print_help()
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
