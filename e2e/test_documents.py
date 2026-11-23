import hashlib

import pytest


pytestmark = pytest.mark.e2e


def test_crud_completo_por_la_interfaz(client, pdf_valido):
    subida = client.post(
        "/api/documents",
        files={"file": ("crud-t10-unico.pdf", pdf_valido, "application/pdf")},
    )
    assert subida.status_code == 201
    id_documento = subida.json()["id"]
    checksum = hashlib.sha256(pdf_valido).hexdigest()

    try:
        listado = client.get("/api/documents")
        assert listado.status_code == 200
        assert any(item["checksum"] == checksum for item in listado.json()["data"])

        respuesta = client.get(f"/api/documents/{id_documento}")
        assert respuesta.status_code == 200

        editado = client.put(
            f"/api/documents/{id_documento}",
            json={"filename": "editado-t10.pdf"},
        )
        assert editado.status_code == 200
        assert editado.json()["filename"] == "editado-t10.pdf"

        id_borrado = id_documento
        eliminado = client.delete(f"/api/documents/{id_borrado}")
        assert eliminado.status_code == 204
        id_documento = None

        inexistente = client.get(f"/api/documents/{id_borrado}")
        assert inexistente.status_code == 404
    finally:
        if id_documento:
            client.delete(f"/api/documents/{id_documento}")
