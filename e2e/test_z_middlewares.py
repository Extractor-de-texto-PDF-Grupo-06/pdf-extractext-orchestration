import concurrent.futures

import httpx
import pytest

from conftest import BASE_URL


pytestmark = pytest.mark.e2e

# Traefik deja pasar una ráfaga de 200 y repone 100 por segundo. Para recibir 429 hay que
# pedir más rápido que eso: con una conexión nueva por pedido el cliente queda cerca de los
# 100 req/s y el bucket no llega a vaciarse, así que se reutilizan las conexiones.
PEDIDOS = 1000
CONEXIONES = 100


def test_ratelimit_publico_responde_429():
    limites = httpx.Limits(max_connections=CONEXIONES, max_keepalive_connections=CONEXIONES)
    with httpx.Client(base_url=BASE_URL, timeout=20.0, limits=limites) as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONEXIONES) as pool:
            codigos = list(pool.map(lambda _: session.get("/documents/").status_code, range(PEDIDOS)))

    assert 429 in codigos
