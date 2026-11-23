import subprocess
import time
from pathlib import Path

import httpx
import pytest

from conftest import BASE_URL
from pdf_factory import make_pdf

RAIZ = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.e2e


def compose(*argumentos):
    return subprocess.run(
        ["docker", "compose", *argumentos],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
    )


def esperar_health(client: httpx.Client, ruta: str = "/api/health"):
    for _ in range(60):
        try:
            respuesta = client.get(ruta)
            if respuesta.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError(f"No se recuperó {ruta}")


def test_circuito_abre_con_el_extractor_apagado(client, pdf_valido):
    clave = "/config/web/circuit_breaker_failure_threshold"
    limite = client.get(clave)
    assert limite.status_code == 200
    valor_original = limite.json()["value"]
    cambio = client.put(clave, json={"value": "5"})
    assert cambio.status_code == 200
    time.sleep(6)

    compose("stop", "extractor")
    try:
        respuestas = []
        for numero in range(6):
            data = make_pdf(f"circuito-{numero}")
            respuesta = client.post(
                "/api/documents",
                files={"file": (f"circuito-{numero}.pdf", data, "application/pdf")},
            )
            respuestas.append(respuesta)

        assert [respuesta.status_code for respuesta in respuestas] == [502] * 5 + [503]
        assert respuestas[-1].headers.get("retry-after")
    finally:
        compose("start", "extractor")
        esperar_health(client, "/extractor/health")
        restaurar = client.put(clave, json={"value": valor_original})
        assert restaurar.status_code == 200
        compose("restart", "web")
        esperar_health(client, "/api/health")


def test_config_caida_usa_respaldo(client, pdf_valido):
    compose("stop", "config")
    id_documento = None
    try:
        time.sleep(6)
        respuesta = client.post(
            "/api/documents",
            files={"file": ("config-caida-unico.pdf", pdf_valido, "application/pdf")},
        )
        assert respuesta.status_code == 201
        id_documento = respuesta.json()["id"]
    finally:
        if id_documento:
            client.delete(f"/api/documents/{id_documento}")
        compose("start", "config")
        esperar_health(client, "/config/health")


def test_cambio_de_limite_en_caliente(client):
    clave = "/config/web/max_file_size_mb"
    limite_original = client.get(clave)
    assert limite_original.status_code == 200
    valor_original = limite_original.json()["value"]
    try:
        cambio = client.put(clave, json={"value": "1"})
        assert cambio.status_code == 200
        time.sleep(6)
        subida = client.post(
            "/api/documents",
            files={
                "file": (
                    "limite-caliente.pdf",
                    make_pdf("limitecaliente", padding_bytes=1024 * 1024 + 128),
                    "application/pdf",
                )
            },
        )
        assert subida.status_code == 413
    finally:
        restaurar = client.put(clave, json={"value": valor_original})
        assert restaurar.status_code == 200
        time.sleep(6)
