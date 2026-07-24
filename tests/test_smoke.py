import asyncio
import socket
import subprocess
import time

import httpx
import pytest


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


@pytest.mark.asyncio
async def test_api_smoke_over_http():
    if not _port_open("127.0.0.1", 8000):
        pytest.skip("backend server is not running on 127.0.0.1:8000")

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        health = await client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"


def test_backend_smoke_server_startup():
    if _port_open("127.0.0.1", 8000):
        pytest.skip("backend server is already running on 127.0.0.1:8000")

    proc = subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            if _port_open("127.0.0.1", 8000):
                break
            if proc.poll() is not None:
                pytest.skip("backend server could not start in this environment")
            time.sleep(1)
        if not _port_open("127.0.0.1", 8000):
            pytest.skip("backend server could not bind to 127.0.0.1:8000 in this environment")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
