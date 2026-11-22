import asyncio
import hashlib

import httpx
import pytest

from conftest import BASE_URL


pytestmark = pytest.mark.e2e


def subir(client: httpx.Client, data: bytes, nombre: str = "prueba.pdf"):
    return client.post(
        "/api/documents",
        files={"file": (nombre, data, "application/pdf")},
    )


def test_subida_valida_y_duplicada(client, pdf_valido):
    primera = subir(client, pdf_valido, "subida-valida.pdf")
    assert primera.status_code == 201
    body = primera.json()
    try:
        assert body["filename"] == "subida-valida.pdf"
        assert body["checksum"] == hashlib.sha256(pdf_valido).hexdigest()
        assert body["page_count"] == 1
        assert isinstance(body["metadata"], dict)

        segunda = subir(client, pdf_valido, "subida-valida.pdf")
        assert segunda.status_code == 409
        assert segunda.json() == {"detail": "Ese PDF ya está guardado."}
    finally:
        client.delete(f"/api/documents/{body['id']}")


def test_subidas_concurrentes_no_guardan_el_mismo_pdf_dos_veces(client, pdf_valido):
    async def pedir():
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as session:
            respuesta = await session.post(
                "/api/documents",
                files={"file": ("concurrencia-unica.pdf", pdf_valido, "application/pdf")},
            )
            return respuesta

    async def ejecutar():
        return await asyncio.gather(pedir(), pedir())

    respuestas = asyncio.run(ejecutar())
    try:
        codigos = sorted(respuesta.status_code for respuesta in respuestas)
        assert codigos == [201, 409]
    finally:
        for respuesta in respuestas:
            if respuesta.status_code == 201:
                client.delete(f"/api/documents/{respuesta.json()['id']}")
