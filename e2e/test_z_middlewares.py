import concurrent.futures

import httpx
import pytest

from conftest import BASE_URL


pytestmark = pytest.mark.e2e


def test_ratelimit_publico_responde_429():
    codigos = []

    def pedir(_):
        with httpx.Client(base_url=BASE_URL, timeout=20.0) as session:
            return session.get("/documents/").status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=300) as pool:
        codigos.extend(pool.map(pedir, range(600)))

    assert 429 in codigos
