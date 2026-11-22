import asyncio

import httpx
import pytest


pytestmark = pytest.mark.e2e


def subir(client: httpx.Client, data: bytes, nombre: str = "prueba.pdf"):
    return client.post(
        "/api/documents",
        files={"file": (nombre, data, "application/pdf")},
    )


def test_subida_valida_y_duplicada(client, pdf_valido):
    primera = subir(client, pdf_valido, "Proyecto T10.pdf")
    assert primera.status_code in (201, 409)

    if primera.status_code == 201:
        body = primera.json()
        assert body["filename"] == "Proyecto T10.pdf"
        assert len(body["checksum"]) == 64
        assert body["page_count"] >= 1
        assert isinstance(body["metadata"], dict)

    segunda = subir(client, pdf_valido, "Proyecto T10.pdf")
    assert segunda.status_code == 409
    assert segunda.json() == {"detail": "Ese PDF ya está guardado."}


def test_subidas_concurrentes_no_guardan_el_mismo_pdf_dos_veces(client, pdf_valido):
    async def pedir():
        async with httpx.AsyncClient(base_url="http://localhost", timeout=30.0) as session:
            respuesta = await session.post(
                "/api/documents",
                files={"file": ("concurrencia.pdf", pdf_valido, "application/pdf")},
            )
            return respuesta.status_code

    async def ejecutar():
        return await asyncio.gather(pedir(), pedir())

    codigos = asyncio.run(ejecutar())
    assert sorted(codigos).count(201) <= 1
    assert sorted(codigos).count(409) >= 1
