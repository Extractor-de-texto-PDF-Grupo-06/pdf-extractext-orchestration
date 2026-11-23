# Informe de carga: extractor detrás de Traefik (T13)

Fecha: 22/11/2026 · Resultados crudos: `load/results/20261122-201608/`

## Qué se probó

El mismo perfil del TP de la cátedra, con los 4 PDFs oficiales (SHA-256 verificados contra
`pdf-extractext-extractor/tests/stress/README.md`), contra `POST /extract` por el entrypoint
interno de Traefik (`http://traefik:8081/extract`, sin rate limit), con 5 réplicas del
extractor de 1 CPU y 1 GB cada una. Los generadores corren en la red del compose.

- **k6 (spike):** 0 → 100 VUs en 10 s, 20 s sostenidos, bajada en 10 s.
- **Vegeta:** 50 req/s durante 30 s, timeout de 30 s.

## Resultados

| Herramienta | Métrica | Resultado | Referencia del profesor | Cumple |
|---|---|---|---|---|
| k6 | Rendimiento | **28,99 req/s** | 25,35 req/s | Sí |
| k6 | Respuestas 200 | 1164 de 1164 (0 % de fallos) | — | — |
| k6 | Latencia (media / p95 / máx.) | 2,66 s / 4,6 s / 5,04 s | — | — |
| Vegeta | Rendimiento efectivo | **25,25 req/s** | 16,65 req/s | Sí |
| Vegeta | Éxito | 92,40 % (1386 × 200) | — | — |
| Vegeta | Errores | 113 × 503 (saturación) y 1 timeout de cliente | — | — |
| Vegeta | Latencia (media / p95 / máx.) | 9,3 s / 25,05 s / 30 s | — | — |

Los 11 contenedores siguieron `healthy` durante y después de las pruebas.

## Lectura

- El extractor detrás de Traefik supera las dos referencias: 14 % más en k6 y 52 % más en
  Vegeta.
- Los `503` de Vegeta son el comportamiento esperado de la admisión del extractor cuando
  se satura (contrato: `503` saturado). Vegeta ataca a 50 req/s con PDFs de hasta 8,9 MB,
  por encima de lo que las 5 réplicas pueden procesar; no es una falla de Traefik.
- Con k6 (concurrencia acotada a 100 VUs) no hubo ningún error.

## Cómo repetirlo

```powershell
docker compose up -d --wait
powershell -File load/run.ps1
```
