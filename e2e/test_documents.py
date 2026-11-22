import pytest


pytestmark = pytest.mark.e2e


def test_crud_completo_por_la_interfaz(client, pdf_valido):
    subida = client.post(
        "/api/documents",
        files={"file": ("crud-t10.pdf", pdf_valido, "application/pdf")},
    )
    if subida.status_code == 409:
        checksum = __import__("hashlib").sha256(pdf_valido).hexdigest()
        encontrados = client.get("/api/documents", params={"checksum": checksum}).json()["data"]
        assert encontrados
        id_documento = encontrados[0]["id"]
    else:
        assert subida.status_code == 201
        id_documento = subida.json()["id"]

    respuesta = client.get(f"/api/documents/{id_documento}")
    assert respuesta.status_code == 200

    editado = client.put(
        f"/api/documents/{id_documento}",
        json={"filename": "editado-t10.pdf"},
    )
    assert editado.status_code == 200
    assert editado.json()["filename"] == "editado-t10.pdf"

    eliminado = client.delete(f"/api/documents/{id_documento}")
    assert eliminado.status_code == 204

    inexistente = client.get(f"/api/documents/{id_documento}")
    assert inexistente.status_code == 404
