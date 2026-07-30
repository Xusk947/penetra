"""Python sandbox tool for agents.

Executes untrusted Python code in a short-lived subprocess or a Docker
container with a strict timeout. It is intended for safe auxiliary tasks
(parsing data, formatting payloads, calculating hashes) rather than arbitrary
system commands.
"""

from __future__ import annotations

import base64
import contextlib
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from langchain.tools import tool

from agents.common.config import Settings

logger = logging.getLogger(__name__)


def _run_local(script: Path, timeout: int) -> dict[str, Any]:
    """Run the script with the local Python interpreter."""
    proc = subprocess.run(
        ["python", str(script)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[:4000],
        "stderr": proc.stderr[:4000],
    }


def _run_docker(script: Path, timeout: int, image: str) -> dict[str, Any]:
    """Run the script inside a short-lived Docker container."""
    docker_command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{script}:/code/script.py:ro",
        image,
        "python",
        "/code/script.py",
    ]
    logger.info("Running Python sandbox in Docker: %s", " ".join(docker_command))
    proc = subprocess.run(
        docker_command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[:4000],
        "stderr": proc.stderr[:4000],
    }


@tool
def python_sandbox(
    code: str,
    timeout: int = 10,
    encode_input: str | None = None,
) -> dict[str, Any] | None:
    """Run Python code in a sandboxed subprocess or Docker container.

    Use this for data processing, encoding/decoding, small scripts and quick
    calculations. The ``code`` argument may be base64-encoded by passing
    ``encode_input="base64"``.

    Set ``PYTHON_USE_DOCKER=true`` in ``.env`` to execute the code inside the
    ``PYTHON_DOCKER_IMAGE`` container (default ``python:3.12-slim``) with no
    network access. The default is a local subprocess for environments without
    Docker.
    """
    if encode_input == "base64":
        try:
            code = base64.b64decode(code).decode("utf-8")
        except Exception as exc:
            return {"error": f"Failed to decode base64 code: {exc}"}

    # If the agent invokes us with a bare URL as the code argument, there is
    # nothing useful to execute. Returning None lets the caller skip creating
    # a finding for this no-op.
    stripped = code.strip()
    if stripped.startswith(("http://", "https://")):
        return None

    # Write code to a temporary file so we avoid quoting issues and long command lines.
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        script = Path(f.name)

    settings = Settings()
    try:
        if settings.python_use_docker:
            return _run_docker(script, timeout, settings.python_docker_image)
        return _run_local(script, timeout)
    except FileNotFoundError as exc:
        return {"error": f"Sandbox executable not found: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": "Code execution exceeded the sandbox timeout", "timeout": timeout}
    except Exception as exc:
        logger.warning("python_sandbox failed: %s", exc)
        return {"error": str(exc)}
    finally:
        with contextlib.suppress(OSError):
            script.unlink(missing_ok=True)
