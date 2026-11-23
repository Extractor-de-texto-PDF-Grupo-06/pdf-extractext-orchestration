# Pruebas de carga a través de Traefik

Mismo perfil que el TP de la cátedra, contra el extractor detrás de Traefik:

- k6 (spike): 0 → 100 VUs en 10 s, 20 s sostenidos, bajada en 10 s.
- Vegeta: 50 req/s durante 30 s, timeout de 30 s.

Entran por el entrypoint interno de Traefik (`http://traefik:8081/extract`), que no tiene
rate limit y es el que usa web. Los generadores corren en la red del compose, así que no
hace falta publicar ningún puerto.

## Uso

1. Copiar en `load/pdfs/` los 4 PDFs oficiales (no se versionan; ver la lista y los
   SHA-256 en el README del repo del extractor, `tests/stress`).
2. Levantar el stack: `docker compose up -d --wait`.
3. `powershell -File load/run.ps1`

Los resultados quedan en `load/results/<fecha>/` (ignorado por Git).

Referencia del profesor: 25,35 req/s en k6 y 16,65 req/s efectivos en Vegeta.
