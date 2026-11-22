"""
Una caída de documents no deja sin rutas al resto del sistema.

Traefik descarta los labels de un contenedor apagado o unhealthy: si los middlewares
compartidos se definieran en documents, con documents caído la interfaz, el extractor y
config responderían 404.
"""
import subprocess
import time
from pathlib import Path

import httpx
import pytest


pytestmark = pytest.mark.e2e

RAIZ = Path(__file__).resolve().parents[1]


def compose(*argumentos):
    return subprocess.run(
        ["docker", "compose", *argumentos],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
    )


def esperar(client: httpx.Client, ruta: str):
    for _ in range(60):
        try:
            if client.get(ruta).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError(f"No se recuperó {ruta}")


def test_con_documents_caido_las_demas_rutas_siguen_respondiendo(client):
    compose("stop", "documents")
    try:
        # Traefik reacciona al evento de Docker; un segundo alcanza para que lo procese.
        time.sleep(1)

        assert client.get("/").status_code == 200
        assert client.get("/extractor/health").status_code == 200
        assert client.get("/config/health").status_code == 200
    finally:
        compose("start", "documents")
        esperar(client, "/documents/")
