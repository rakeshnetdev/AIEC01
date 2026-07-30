"""Custom in-process tools for the concierge (an SDK MCP server, no networking).

Both tools are read-only and refuse to touch anything outside TARGET_REPO.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .config import TARGET_REPO


class OutsideRepoError(ValueError):
    """Raised when a requested path escapes the target repository."""


def _resolve_in_repo(raw_path: str) -> Path:
    """Resolve `raw_path` (absolute or repo-relative) inside TARGET_REPO."""
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = TARGET_REPO / candidate
    resolved = candidate.resolve()
    if resolved != TARGET_REPO and TARGET_REPO not in resolved.parents:
        raise OutsideRepoError(f"{raw_path} is outside {TARGET_REPO}")
    return resolved


def _text(message: str, *, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": message}]}
    if is_error:
        result["is_error"] = True
    return result


@tool(
    "count_lines",
    "Count lines in a file, or the largest files under a directory of the "
    "target repository. Use for size/complexity questions.",
    {"path": str, "top": int},
)
async def count_lines(args: dict[str, Any]) -> dict[str, Any]:
    """`path` is a file or directory (repo-relative); `top` limits directory output."""
    try:
        target = _resolve_in_repo(args.get("path") or ".")
    except OutsideRepoError as exc:
        return _text(f"Refused: {exc}", is_error=True)

    if not target.exists():
        return _text(f"Not found: {target}", is_error=True)

    def count(path: Path) -> int:
        with path.open("rb") as handle:
            return sum(1 for _ in handle)

    if target.is_file():
        return _text(f"{target.relative_to(TARGET_REPO)}: {count(target)} lines")

    top = int(args.get("top") or 10)
    skip = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache"}
    sizes: list[tuple[int, Path]] = []
    for path in target.rglob("*"):
        if not path.is_file() or skip & set(path.parts):
            continue
        try:
            sizes.append((count(path), path))
        except OSError:
            continue

    if not sizes:
        return _text(f"No readable files under {target.relative_to(TARGET_REPO)}")

    sizes.sort(reverse=True)
    total = sum(n for n, _ in sizes)
    header = (
        f"{len(sizes)} files, {total} lines under "
        f"{target.relative_to(TARGET_REPO)}. Largest {min(top, len(sizes))}:"
    )
    rows = "\n".join(
        f"  {n:>7}  {p.relative_to(TARGET_REPO)}" for n, p in sizes[:top]
    )
    return _text(f"{header}\n{rows}")


@tool(
    "git_log",
    "Recent git history of the target repository: commit hash, date, author, "
    "subject. Optionally filter to one path. Use for 'what changed lately' "
    "questions, which files are hot, or who owns an area.",
    {"limit": int, "path": str},
)
async def git_log(args: dict[str, Any]) -> dict[str, Any]:
    """History is not in the files, so Read/Grep can never answer this."""
    limit = max(1, min(int(args.get("limit") or 15), 100))
    command = ["git", "log", f"-{limit}", "--date=short", "--pretty=%h %ad %an: %s"]

    raw_path = args.get("path")
    if raw_path:
        try:
            target = _resolve_in_repo(raw_path)
        except OutsideRepoError as exc:
            return _text(f"Refused: {exc}", is_error=True)
        command += ["--", str(target)]

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(TARGET_REPO),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    except TimeoutError:
        process.kill()
        return _text("git log timed out", is_error=True)

    if process.returncode != 0:
        return _text(
            f"git log failed: {stderr.decode(errors='replace').strip()}", is_error=True
        )

    output = stdout.decode(errors="replace").strip()
    scope = f" for {raw_path}" if raw_path else ""
    return _text(f"Last {limit} commits{scope}:\n{output}" if output else "No commits.")


concierge_server = create_sdk_mcp_server(
    name="concierge",
    version="1.0.0",
    tools=[count_lines, git_log],
)
