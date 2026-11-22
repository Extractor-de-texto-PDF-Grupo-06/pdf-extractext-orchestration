from pathlib import Path


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
