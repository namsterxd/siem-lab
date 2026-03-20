from __future__ import annotations

import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .config import ROOT


def _run(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        check=False,
        capture_output=capture_output,
        env=os.environ.copy(),
    )


def docker_available() -> bool:
    return shutil.which("docker") is not None


def compose_available() -> bool:
    result = _run(["docker", "compose", "version"], capture_output=True)
    return result.returncode == 0


def ensure_docker() -> None:
    if not docker_available():
        raise RuntimeError("Docker is not installed or not on PATH.")


def compose_install_supported() -> bool:
    return platform.system() == "Linux"


def compose_install_help() -> str:
    system_name = platform.system()
    if system_name == "Darwin":
        return "Install Docker Desktop for macOS so `docker compose` is available, then rerun `./lab bootstrap`."
    if system_name == "Windows":
        return "Use WSL2 with Docker Desktop integration, or install Docker with Compose support before rerunning `./lab bootstrap`."
    if system_name == "Linux":
        return "Install Docker Compose or allow the lab to place the compose plugin in $HOME/.docker/cli-plugins."
    return f"Install Docker Compose for {system_name} before rerunning `./lab bootstrap`."


def install_compose_plugin(version: str) -> Path:
    if not compose_install_supported():
        raise RuntimeError(compose_install_help())
    docker_config = Path(os.environ.get("DOCKER_CONFIG", Path.home() / ".docker"))
    plugin_dir = docker_config / "cli-plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    target = plugin_dir / "docker-compose"
    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    machine = platform.machine().lower()
    arch = arch_map.get(machine)
    if arch is None:
        raise RuntimeError(f"Unsupported architecture for compose install: {machine}")
    url = f"https://github.com/docker/compose/releases/download/{version}/docker-compose-linux-{arch}"
    with urllib.request.urlopen(url) as response:
        target.write_bytes(response.read())
    target.chmod(0o755)
    return target


def compose(*args: str) -> None:
    command = ["docker", "compose", *args]
    result = _run(command)
    if result.returncode != 0:
        raise RuntimeError(f"Compose command failed: {' '.join(command)}")


def docker_logs(container_name: str, since_iso: str) -> str:
    result = _run(["docker", "logs", "--since", since_iso, container_name], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to fetch logs for {container_name}")
    return result.stdout
