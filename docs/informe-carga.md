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

## Corridas del 23/11

Se repitió la prueba con el cliente de League of Legends cerrado (resultados en
`load/results/20261123-014948/`, `-015145/` y `-015343/`). Antes de cerrarlo, dos corridas
dieron 4,58 y 20,97 req/s en k6 (`-014402/` y `-014630/`): el uso del equipo afecta mucho.

| Corrida | k6 req/s | k6 mediana / p95 | Vegeta req/s efectivos | Vegeta éxito | Vegeta p50 / p95 |
|---|---|---|---|---|---|
| 1 | 38,43 | 1,93 s / 3,57 s | 28,56 | 99,53 % | 4,85 s / 13,60 s |
| 2 | 38,73 | 2,19 s / 3,13 s | 27,64 | 98,60 % | 5,26 s / 18,47 s |
| 3 | 40,85 | 1,76 s / 3,79 s | 29,43 | 99,73 % | 4,65 s / 12,60 s |

Con el equipo sin otras aplicaciones pesadas, el sistema supera las dos referencias del
profesor en las tres corridas, sin fallos en k6.

## Lectura

- El extractor detrás de Traefik supera las dos referencias del profesor en las corridas con
  el equipo libre (38–41 req/s en k6 y 28–29 en Vegeta); en la del 22/11, 14 % y 52 % más.
- Los `503` de Vegeta son el comportamiento esperado de la admisión del extractor cuando
  se satura (contrato: `503` saturado), y con el equipo libre bajan a menos del 2 %.
- Con k6 (concurrencia acotada a 100 VUs) no hubo ningún error.
- Los resultados dependen de la carga del equipo: con otras aplicaciones abiertas, una
  corrida dio solo 4,58 req/s en k6.

## Comparación con nginx

El criterio original de T13 pedía comparar contra el balanceador anterior. Los datos de
nginx son del repo del extractor
([`docs/refactor-2026-10-08.md`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-extractor/blob/develop/docs/refactor-2026-10-08.md)),
con el mismo código del extractor que corre hoy en `develop` y los mismos 4 PDFs.

| Balanceador | k6 req/s | k6 mediana / p95 | Vegeta req/s efectivos | Vegeta éxito |
|---|---|---|---|---|
| nginx (`least_conn`), 3 corridas | 35,91 – 37,54 | 2,37 – 2,42 s / 2,88 – 3,09 s | 33,15 – 36,72 | 100 % |
| Traefik, 3 corridas del 23/11 | 38,43 – 40,85 | 1,76 – 2,19 s / 3,13 – 3,79 s | 27,64 – 29,43 | 98,6 – 99,7 % |

Los dos quedan en el mismo orden de magnitud: Traefik rinde algo más en k6 y nginx algo más
en Vegeta, con éxito cercano al 100 % en ambos. Ninguno es claramente mejor. La comparación
**no es del todo equivalente**:

- nginx se midió con puertos publicados en el host y generadores con límites de CPU y RAM
  (k6 2 CPU / 3 GiB, Vegeta 1 CPU / 1 GiB), en Docker Desktop con 12 CPU lógicas y 7,71 GiB,
  que coincide con la VM de esta máquina.
- Traefik se midió con los generadores dentro de la red del compose y sin límites, en un
  stack de 11 contenedores (con documents, MongoDB, config y Consul encendidos).
- La variación entre corridas, sobre todo con otras aplicaciones abiertas, es del mismo
  orden que la diferencia entre balanceadores.

Por eso no se puede atribuir la diferencia solo al balanceador. La comparación justa es
repetir las dos configuraciones con el mismo método.

Las cifras de 15,70 req/s (k6) y 4,36 req/s (Vegeta) del informe del extractor son de una
versión anterior del código, sin la optimización de memoria compartida: no sirven para
comparar balanceadores.

## Cómo repetirlo

```powershell
docker compose up -d --wait
powershell -File load/run.ps1
```
