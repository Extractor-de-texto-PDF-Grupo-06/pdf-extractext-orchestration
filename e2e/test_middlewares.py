import concurrent.futures

import httpx
import pytest


pytestmark = pytest.mark.e2e


def test_ratelimit_publico_responde_429():
    codigos = []

    def pedir(_):
        with httpx.Client(base_url="http://localhost", timeout=10.0) as session:
            return session.get("/documents/").status_code

    for inicio in range(0, 1500, 300):
        with concurrent.futures.ThreadPoolExecutor(max_workers=300) as pool:
            codigos.extend(pool.map(pedir, range(inicio, inicio + 300)))

    assert 429 in codigos
