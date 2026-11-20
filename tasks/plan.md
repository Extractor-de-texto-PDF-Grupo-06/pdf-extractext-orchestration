# Plan de implementación: pdf-extractext en microservicios

Especificación: [`SPEC.md`](../SPEC.md) · Entrega: miércoles 25/11/2026

Las tareas se siguen como issues en el Project **Migración a microservicios** de la
organización. Cada issue vive en el repositorio que toca; esta lista es el índice.

## Resumen

Pasar del repositorio actual (documents más el despliegue de todo el sistema) a seis
repositorios: el monolito archivado, la orquestación y cuatro microservicios (web,
documents, extractor y config), con Traefik como puerta de entrada y Consul como
configuración centralizada. Cada fase deja el sistema funcionando, para poder entregar
aunque se corte la siguiente.

## Decisiones de arquitectura

Registradas en [`docs/adr/`](../docs/adr/): un repositorio por servicio y el monolito
archivado (0001), Traefik con labels de Docker (0002), config como único cliente de Consul
(0003), web como orquestador con el circuit breaker (0004), web llega al extractor por
Traefik (0005), comunicación síncrona (0006) y metadatos en el extractor (0007).

## Grafo de dependencias

```
T1 docs y forma de trabajo
 └─ T2 documents con historial ─── T3 monolito restaurado y archivado
                │
                ├─ T5 documents recortado ─────────┐
T4 config ──────┼──────────────────────────────────┤
T6 extractor con metadatos (PR a valendotjpg) ─────┤
                └─ T7 web ─────────────────────────┤
                                                   ▼
                              T8 compose ── T9 middlewares ── T10 e2e
                                                   │
                         T11 imágenes en GHCR ── T12 seguridad ── T13 carga
                                                   │
                                     T14 documentación ── T15 guía de la defensa
```

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El PR del extractor depende de que valendotjpg lo revise | Medio: bloquea los metadatos | Pedirle la revisión el sábado; web tolera `metadata` ausente |
| Traefik rinde menos que el nginx afinado para PDFs grandes | Medio: criterio de rendimiento | T13 mide temprano; si no alcanza, ajustar o justificar con datos |
| Docker en Windows convierte los finales de línea de los scripts | Bajo | `.gitattributes` con `eol=lf` en cada repositorio |
| El tiempo no alcanza | Alto | Fases cortables: sin T14 y T15 igual se entrega; T11 tiene alternativa con etiquetas de Git |

## Lista de tareas

Tamaño: S (1–2 archivos) · M (3–5) · L (5 o más, dividido en commits rojo y verde).

### Fase 0 — Fundaciones (viernes 20)

#### T1 · orchestration · Documentación y forma de trabajo · S

Subir `SPEC.md`, `docs/GLOSSARY.md`, `docs/adr/`, `docs/workflow.md` y este plan.
Configurar en los seis repositorios: rama `develop` por defecto, `main` y `develop`
protegidas, CODEOWNERS con cotthss y plantilla de pull request.

- [ ] Los documentos están en `develop` de orchestration.
- [ ] Un push directo a `main` o `develop` es rechazado en cualquier repositorio.
- [ ] Un pull request pide la aprobación de cotthss.

**Dependencias:** ninguna.

#### T2 · documents · Separar documents conservando el historial · M

Crear `pdf-extractext-documents` a partir de `main` de `pdf-extractext`, con todo su
historial, antes de restaurar el monolito.

- [ ] `git log` de documents muestra los commits del monolito y de la migración.
- [ ] Los 115 tests unitarios pasan en el repositorio nuevo.

**Verificación:** `uv run pytest tests/unit`. **Dependencias:** T1.

#### T3 · pdf-extractext · Restaurar y archivar el monolito · M

- [ ] `docker compose up` del commit `5b38628` levanta y sube un PDF.
- [ ] `main` tiene el contenido de `5b38628` en un commit nuevo; el historial queda.
- [ ] Etiqueta `monolito-v1`; el README explica que es la Etapa 1 y enlaza a orchestration.
- [ ] El repositorio está archivado.

**Dependencias:** T2.

### Checkpoint A
- [ ] Seis repositorios con `develop`, CODEOWNERS y protección.
- [ ] El monolito archivado levanta; documents conserva su historial.

### Fase 1 — Servicios (viernes 20 y sábado 21)

#### T4 · config · Microservicio de configuración · L

CRUD sobre el KV de Consul con `py-consul`, según el contrato de la especificación. Capas
`presentation`, `application` e `infrastructure` con test de arquitectura. Dockerfile
multi-stage, CI con tests.

- [ ] El contrato completo responde como dice la especificación, incluido `409` en
      check-and-set.
- [ ] `GET /health` responde `503` si Consul no tiene líder.
- [ ] El test de arquitectura falla si `application` importa una librería externa.

**Verificación:** `uv run pytest`; `uv run pytest -m integration` contra Consul.
**Dependencias:** ninguna.

#### T5 · documents · Dejar documents como CRUD puro · L

Quitar la interfaz, `/api/v1/extract`, el alias `/extract`, el cliente del extractor, el
circuit breaker, el descubrimiento con Consul, pypdf, el compose, nginx y `consul/`.
Rutas en la raíz según el contrato, con `POST /` y `GET /?checksum=`. `GET /health`
consulta MongoDB. El índice único pasa a un comando de administración
(`python -m app.admin.create_indexes`). Python 3.12, `PORT`, Dockerfile multi-stage, CI.

- [ ] Los tests del contrato nuevo pasan; los del código quitado se eliminan con él.
- [ ] `grep -r pypdf` no encuentra nada.
- [ ] Dos `POST /` con el mismo checksum: uno `201` y otro `409`.

**Dependencias:** T2.

#### T6 · extractor · Metadatos en la respuesta (PR a valendotjpg) · M

- [ ] `POST /extract` devuelve `metadata` (autor, título, fechas) además de `content` y
      `page_count`.
- [ ] Los scripts de k6 y Vegeta del TP siguen pasando sin cambios.
- [ ] Dockerfile con usuario de UID fijo y `PORT`; el compose del TP pasa todas las variables.

**Dependencias:** ninguna.

#### T7 · web · Interfaz y orquestador · L

Tres cortes verticales, cada uno con rojo y verde:

1. **Subida:** caso de uso `UploadDocument` con puertos `Extractor`, `DocumentStore` y
   `ConfigSource`; el circuit breaker y sus tests vienen de documents.
2. **Configuración:** adaptador de config con caché de 5 segundos y respaldo en `Settings`.
3. **CRUD e interfaz:** reenvío a documents y la interfaz que hoy sirve documents.

- [ ] La subida responde los códigos del contrato, incluido `503` con `Retry-After`.
- [ ] Con config caído, la subida usa los valores de `Settings`.
- [ ] Test de arquitectura en verde.

**Dependencias:** T4 y T5 (contratos), T6 (opcional: tolera `metadata` ausente).

### Checkpoint B
- [ ] Los cuatro servicios con tests en verde y su imagen construida.

### Fase 2 — Orquestación (sábado 21 y domingo 22)

#### T8 · orchestration · Compose del sistema · L

Traefik v3.6 con entrypoints `web` (80) e interno (no publicado), panel en 8080. Consul
en modo servidor con volumen, interfaz en `consul.localhost`. MongoDB con usuario,
volumen y sin puerto. Procesos de una sola vez: índices de documents y claves iniciales
de config. Extractor con 5 réplicas. `read_only`, `cap_drop: [ALL]` y `no-new-privileges`
en los contenedores propios. `docker-compose.build.yml` para construir desde los repos
clonados al lado.

- [ ] `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build --wait`
      termina con todo sano.
- [ ] `docker compose ps` muestra puertos publicados solo en Traefik.

**Dependencias:** Checkpoint B.

#### T9 · orchestration · Rate limit y retry en Traefik · S

- [ ] Una ráfaga sobre `/documents` por encima del límite recibe `429`.
- [ ] El entrypoint interno del extractor no tiene rate limit.

**Dependencias:** T8.

#### T10 · orchestration · Tests de extremo a extremo · M

Por Traefik: subida, duplicado (también concurrente), CRUD, circuito abierto con el
extractor apagado, cambio de configuración en caliente, config caído y `429`.

- [ ] `uv run pytest -m e2e` en verde con el stack levantado.

**Dependencias:** T9.

### Checkpoint C
- [ ] Criterios funcionales de la especificación cumplidos y probados por T10.

### Fase 3 — Calidad (domingo 22 y lunes 23)

#### T11 · todos · Imágenes en GHCR · M

La CI de cada servicio publica `ghcr.io/extractor-de-texto-pdf-grupo-06/<repo>` con el
hash del commit y `latest` al fusionar en `main`. `docker-compose.yml` usa solo imágenes.

- [ ] `docker compose up -d --wait` sin clonar ningún repositorio levanta el sistema.

**Alternativa si no alcanza el tiempo:** construir desde etiquetas de Git (`v1.0.0`).
**Dependencias:** T8.

#### T12 · todos · Seguridad · M

`pip-audit` y Trivy en la CI de cada servicio.

- [ ] Sin vulnerabilidades altas ni críticas, o cada una justificada en el README.
- [ ] Todos los criterios de seguridad de Docker de la especificación cumplidos.

**Dependencias:** T11.

#### T13 · orchestration · Pruebas de carga a través de Traefik · M

- [ ] k6 y Vegeta del TP superan 25,35 req/s y 16,65 req/s efectivos.
- [ ] Informe con los resultados y la comparación contra nginx.

**Dependencias:** T8.

### Checkpoint D
- [ ] Los doce factores de la especificación tildados, con evidencia.

### Fase 4 — Cierre (martes 24)

#### T14 · todos · Documentación · M
README de cada repositorio; arquitectura y tabla de los doce factores con evidencia en
orchestration.

#### T15 · Guía de la defensa · S
Actualizar las preguntas 3, 6 a 9, 11 a 25 y los puntos débiles con la arquitectura nueva.

### Miércoles 25
Margen para imprevistos y entrega.
