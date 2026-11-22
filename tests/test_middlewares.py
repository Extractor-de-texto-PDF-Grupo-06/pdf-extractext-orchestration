from pathlib import Path

import yaml


RAIZ = Path(__file__).resolve().parents[1]
COMPOSE = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")


def test_los_middlewares_publicos_se_definen_una_vez():
    assert COMPOSE.count("traefik.http.middlewares.public-rate-limit.ratelimit.average=") == 1
    assert COMPOSE.count("traefik.http.middlewares.public-retry.retry.attempts=") == 1


def test_las_rutas_publicas_aplican_rate_limit_y_retry():
    for ruta in ("documents", "extractor", "config", "web"):
        linea = next(
            linea for linea in COMPOSE.splitlines()
            if f"traefik.http.routers.{ruta}.middlewares=" in linea
        )
        assert "public-rate-limit" in linea
        assert "public-retry" in linea


def test_el_entrypoint_interno_del_extractor_no_tiene_rate_limit():
    inicio = COMPOSE.index("traefik.http.routers.extractor-interno.rule")
    final = COMPOSE.index("traefik.http.services.extractor.loadbalancer.server.port", inicio)
    router_interno = COMPOSE[inicio:final]

    assert "rate-limit" not in router_interno


def test_el_entrypoint_interno_del_extractor_tiene_retry_sin_rate_limit():
    assert "traefik.http.middlewares.internal-extractor-retry.retry.attempts=" in COMPOSE
    assert "traefik.http.routers.extractor-interno.middlewares=internal-extractor-retry" in COMPOSE

    inicio = COMPOSE.index("traefik.http.routers.extractor-interno.rule")
    final = COMPOSE.index("traefik.http.services.extractor.loadbalancer.server.port", inicio)
    router_interno = COMPOSE[inicio:final]

    assert "internal-extractor-retry" in router_interno
    assert "public-rate-limit" not in router_interno


def test_los_valores_predeterminados_cumplen_la_especificacion():
    assert "${TRAEFIK_RATE_LIMIT_AVERAGE:-100}" in COMPOSE
    assert "${TRAEFIK_RATE_LIMIT_BURST:-200}" in COMPOSE
    assert "${TRAEFIK_RETRY_ATTEMPTS:-3}" in COMPOSE


def _labels(servicio):
    return servicio.get("labels", [])


def _middlewares_definidos(servicio):
    return {
        label.split(".")[3]
        for label in _labels(servicio)
        if label.startswith("traefik.http.middlewares.")
    }


def _middlewares_usados(servicio):
    usados = set()
    for label in _labels(servicio):
        clave, _, valor = label.partition("=")
        if clave.startswith("traefik.http.routers.") and clave.endswith(".middlewares"):
            usados.update(nombre.strip().removesuffix("@docker") for nombre in valor.split(","))
    return usados


def test_cada_router_usa_middlewares_de_su_contenedor_o_de_traefik():
    # Traefik descarta los labels de un contenedor apagado o unhealthy. Si un middleware
    # compartido se define en un servicio, cuando ese servicio cae las rutas de los
    # demás quedan con error y responden 404.
    servicios = yaml.safe_load(COMPOSE)["services"]
    compartidos = _middlewares_definidos(servicios["traefik"])

    for nombre, servicio in servicios.items():
        disponibles = _middlewares_definidos(servicio) | compartidos
        faltantes = _middlewares_usados(servicio) - disponibles
        assert not faltantes, f"{nombre} usa middlewares definidos en otro servicio: {faltantes}"


def test_los_middlewares_publicos_viven_en_traefik():
    traefik = yaml.safe_load(COMPOSE)["services"]["traefik"]

    assert "traefik.enable=true" in _labels(traefik)
    assert {"public-rate-limit", "public-retry"} <= _middlewares_definidos(traefik)
