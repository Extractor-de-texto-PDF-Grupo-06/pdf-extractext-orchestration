# Informe de carga: extractor detrás de Traefik (T13)

Fecha: 22/11/2026 · Resultados: `load/results/20261122-201608/` (versionados; `vegeta.bin`,
de ~100 MB, no)

## Entorno de medición

| | |
|---|---|
| Host | Intel Core i5-10400F (6 núcleos / 12 hilos, 2,9 GHz), 15,9 GB de RAM, Windows 11 Pro |
| Docker | Docker Desktop 29.9.2 (VM con 12 CPU y 7,7 GB de RAM), Compose 5.6.1 |
| Réplicas del extractor | 5, de 1 CPU y 1 GB cada una |
| Generadores de carga | k6 y Vegeta en contenedores dentro de la red del compose, sin límites de recursos |
| Sistema | 11 contenedores del compose, todos `healthy` (ver `servicios.txt`) |

Los generadores y el sistema compiten por la CPU del mismo host.

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

## Comparación con nginx

El criterio original de T13 pedía comparar contra el balanceador anterior. Los datos de
nginx son del repo del extractor
([`docs/refactor-2026-10-08.md`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-extractor/blob/develop/docs/refactor-2026-10-08.md)),
con el mismo código del extractor que corre hoy en `develop` y los mismos 4 PDFs.

| Balanceador | k6 req/s | k6 mediana / p95 | Vegeta req/s efectivos | Vegeta éxito |
|---|---|---|---|---|
| nginx (`least_conn`), 3 corridas | 35,91 – 37,54 | 2,37 – 2,42 s / 2,88 – 3,09 s | 33,15 – 36,72 | 100 % |
| Traefik (esta corrida) | 28,99 | 2,66 s / 4,6 s | 25,25 | 92,40 % |

Con estos números nginx rinde más que Traefik, y no hay que presentarlo al revés. Antes de
atribuirlo a Traefik hay que tener en cuenta que **los entornos no son iguales**:

- nginx se midió con puertos publicados en el host y generadores con límites de CPU y RAM
  (k6 2 CPU / 3 GiB, Vegeta 1 CPU / 1 GiB), en Docker Desktop con 12 CPU lógicas.
- Traefik se midió con los generadores dentro de la red del compose y sin límites, en un
  stack de 11 contenedores (con documents, MongoDB, config y Consul encendidos).

Por eso la diferencia no se puede atribuir solo al balanceador. La comparación justa es
repetir las dos configuraciones en el mismo equipo y con el mismo método.

Las cifras de 15,70 req/s (k6) y 4,36 req/s (Vegeta) del informe del extractor son de una
versión anterior del código, sin la optimización de memoria compartida: no sirven para
comparar balanceadores.

## Cómo repetirlo

```powershell
docker compose up -d --wait
powershell -File load/run.ps1
```
