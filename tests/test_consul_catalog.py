"""Traefik lee las rutas de Docker y del catálogo de Consul (ADR 0008)."""

import json
from pathlib import Path

import yaml

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"


def _servicios():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]


def _etiquetas_de_config():
    return json.loads(_servicios()["config"]["environment"]["SERVICE_TAGS"])


def test_traefik_lee_rutas_de_docker_y_de_consul():
    comando = _servicios()["traefik"]["command"]

    assert "--providers.docker=true" in comando
    assert "--providers.consulcatalog=true" in comando
    assert "--providers.consulcatalog.endpoint.address=consul:8500" in comando
    # Como con Docker: solo enruta lo que se pide con traefik.enable=true.
    assert "--providers.consulcatalog.exposedbydefault=false" in comando


def test_config_se_registra_en_consul_y_no_tiene_labels_de_traefik():
    config = _servicios()["config"]

    assert str(config["environment"]["SERVICE_REGISTRATION"]).lower() == "true"
    # Una sola fuente para su ruta: si también tuviera labels, Traefik armaría dos routers.
    assert not [label for label in config.get("labels", []) if label.startswith("traefik.")]


def test_la_ruta_de_config_sale_del_catalogo_de_consul():
    etiquetas = _etiquetas_de_config()

    assert "traefik.enable=true" in etiquetas
    assert "traefik.http.routers.config.rule=PathPrefix(`/config`)" in etiquetas
    assert "traefik.http.routers.config.entrypoints=web" in etiquetas


def test_la_ruta_de_consul_usa_los_middlewares_publicos_definidos_en_docker():
    # Un middleware de otro provider se nombra con su sufijo: public-rate-limit@docker.
    usados = []
    for etiqueta in _etiquetas_de_config():
        clave, _, valor = etiqueta.partition("=")
        if clave.startswith("traefik.http.routers.") and clave.endswith(".middlewares"):
            usados += [nombre.strip() for nombre in valor.split(",")]

    assert "public-rate-limit@docker" in usados
    assert "public-retry@docker" in usados
