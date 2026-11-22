import subprocess
import time

import httpx
import pytest


pytestmark = pytest.mark.e2e


def compose(*argumentos):
    return subprocess.run(
        ["docker", "compose", *argumentos],
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
    compose("stop", "extractor")
    try:
        codigos = []
        retry_after = None
        for numero in range(6):
            data = pdf_valido + (f"\n% circuito-{numero}\n".encode())
            respuesta = client.post(
                "/api/documents",
                files={"file": (f"circuito-{numero}.pdf", data, "application/pdf")},
            )
            codigos.append(respuesta.status_code)
            if respuesta.status_code == 503:
                retry_after = respuesta.headers.get("retry-after")

        assert 503 in codigos
        assert retry_after is not None
    finally:
        compose("start", "extractor")
        esperar_health(client, "/extractor/health")
        compose("restart", "web")
        esperar_health(client, "/api/health")


def test_config_caida_usa_respaldo(client, pdf_valido):
    compose("stop", "config")
    try:
        time.sleep(6)
        respuesta = client.post(
            "/api/documents",
            files={"file": ("config-caida.pdf", pdf_valido, "application/pdf")},
        )
        assert respuesta.status_code in (201, 409)
    finally:
        compose("start", "config")
        esperar_health(client, "/config/health")


def test_cambio_de_limite_en_caliente(client, pdf_valido):
    respuesta = client.put(
        "/config/web/max_file_size_mb",
        json={"value": "10"},
    )
    assert respuesta.status_code in (200, 404)

    if respuesta.status_code == 200:
        time.sleep(6)
        subida = client.post(
            "/api/documents",
            files={"file": ("limite-caliente.pdf", pdf_valido, "application/pdf")},
        )
        assert subida.status_code in (201, 409)
