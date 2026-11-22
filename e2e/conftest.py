import subprocess
import time
from pathlib import Path

import httpx
import pytest


BASE_URL = "http://localhost"
RAIZ = Path(__file__).resolve().parents[1]
PDF = RAIZ.parent.parent / "pdf-extractext-config" / "docs" / "Proyecto 2026 Desarrollo de Software Etapa N°1.pdf"


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=75.0) as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def esperar_stack():
    subprocess.run(["docker", "compose", "start", "extractor", "config"], check=True, capture_output=True)
    subprocess.run(["docker", "compose", "restart", "web"], check=True, capture_output=True)
    time.sleep(3)

    with httpx.Client(base_url=BASE_URL, timeout=5.0) as session:
        for _ in range(60):
            try:
                respuesta = session.get("/api/health")
                if respuesta.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
    pytest.fail("El stack no estuvo disponible en 60 segundos")


@pytest.fixture
def pdf_valido():
    assert PDF.exists(), f"No existe el PDF de prueba: {PDF}"
    return PDF.read_bytes()
