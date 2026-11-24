"""Traefik muestra los dos providers y enruta config con lo que config registró en Consul."""

import os

import httpx
import pytest


pytestmark = pytest.mark.e2e

TRAEFIK_API = os.getenv("E2E_TRAEFIK_API", "http://localhost:8080")


@pytest.fixture
def traefik():
    with httpx.Client(base_url=TRAEFIK_API, timeout=10.0) as session:
        yield session


def test_el_panel_de_traefik_muestra_docker_y_consul(traefik):
    proveedores = traefik.get("/api/overview").json()["providers"]

    assert "Docker" in proveedores
    assert "ConsulCatalog" in proveedores


def test_la_ruta_de_config_viene_del_catalogo_de_consul(traefik, client):
    router = traefik.get("/api/http/routers/config@consulcatalog")

    assert router.status_code == 200
    assert router.json()["status"] == "enabled"
    assert client.get("/config/health").status_code == 200
