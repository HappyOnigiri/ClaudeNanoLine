#!/usr/bin/env python3
"""Repository CI runner."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"

TASKS: list[tuple[str, str]] = [
    ("ruff-format", "ruff format claude-nano-line.py tests/"),
    ("ruff-check", "ruff check claude-nano-line.py tests/ --fix"),
    ("unittest", f"{sys.executable} -m unittest discover -v tests/"),
]

MUTATING_TASK_NAMES = {"ruff-format", "ruff-check"}


def run_task(name: str, command: str) -> tuple[bool, str, str]:
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output, _ = process.communicate()
        return process.returncode == 0, name, output
    except Exception as exc:
        return False, name, str(exc)


def _run_and_record(name: str, command: str, results: dict[str, tuple[bool, str]]) -> None:
    success, _, output = run_task(name, command)
    results[name] = (success, output)
    with open(_log_filename(name), "w", encoding="utf-8") as handle:
        handle.write(output)


def _log_filename(name: str) -> str:
    safe_name = name.replace(" ", "_").replace("/", "_")
    return os.path.join(".logs", f"{safe_name}.log")


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")

    os.makedirs(".logs", exist_ok=True)
    results: dict[str, tuple[bool, str]] = {}

    mutating_tasks = [(name, cmd) for name, cmd in TASKS if name in MUTATING_TASK_NAMES]
    non_mutating_tasks = [(name, cmd) for name, cmd in TASKS if name not in MUTATING_TASK_NAMES]

    for name, cmd in mutating_tasks:
        _run_and_record(name, cmd, results)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_task, name, cmd) for name, cmd in non_mutating_tasks]
        for future in as_completed(futures):
            success, name, output = future.result()
            results[name] = (success, output)
            with open(_log_filename(name), "w", encoding="utf-8") as handle:
                handle.write(output)

    sys.stdout.write("\033[0m")
    sys.stdout.flush()

    failed_tasks: list[tuple[str, str]] = []
    print("\n" + "-" * 60, flush=True)
    for task_name, _ in TASKS:
        success, output = results[task_name]
        if success:
            status_text = f"{COLOR_GREEN}SUCCESS{COLOR_RESET}"
            symbol = "[+]"
        else:
            status_text = f"{COLOR_RED}FAILED{COLOR_RESET}"
            symbol = "[-]"
            failed_tasks.append((task_name, output))
        print(f"  {symbol} {task_name:<35} {status_text}", flush=True)
    print("-" * 60, flush=True)

    if failed_tasks:
        print(f"\n{COLOR_RED}CI FAILED ({len(failed_tasks)} tasks failed){COLOR_RESET}", flush=True)
        print("=" * 80, flush=True)
        for task_name, output in failed_tasks:
            print(f"\n--- Detailed log for {task_name} ---", flush=True)
            print(output, flush=True)
        sys.exit(1)

    print(f"\n{COLOR_GREEN}CI SUCCESSFUL{COLOR_RESET}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
