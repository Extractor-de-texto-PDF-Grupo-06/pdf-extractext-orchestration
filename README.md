# pdf-extractext-orchestration

Despliegue del sistema completo de pdf-extractext: Traefik como única puerta de entrada,
los cuatro microservicios, Consul para la configuración centralizada y MongoDB.
Ningún repositorio de servicio despliega a los demás: eso vive solo acá (factor I).

La especificación está en [`SPEC.md`](SPEC.md), las decisiones en [`docs/adr/`](docs/adr/)
y la forma de trabajo en [`docs/workflow.md`](docs/workflow.md).

## Repositorios

| Repositorio | Qué es |
|---|---|
| [`pdf-extractext-web`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-web) | Interfaz y orquestador de la subida |
| [`pdf-extractext-documents`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-documents) | CRUD de documentos sobre MongoDB |
| [`pdf-extractext-extractor`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-extractor) | PDF → texto, páginas y metadatos |
| [`pdf-extractext-config`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-config) | CRUD de la configuración sobre Consul |
| [`pdf-extractext`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext) | El monolito de la Etapa 1, archivado |

## Cómo levantarlo

Requisitos: Docker con Compose v2.

```bash
cp .env.example .env          # completar MONGO_ROOT_PASSWORD (solo letras y números)
```

**Con las imágenes publicadas en ghcr**, que son públicas: no hace falta iniciar sesión
ni clonar los repositorios de los servicios.

```bash
docker compose pull
docker compose up -d --wait
```

**Construyendo desde el código**, con los cuatro repositorios de servicio clonados al
lado de este:

```
extractor/
├── pdf-extractext-orchestration   ← acá se corre el comando
├── pdf-extractext-web
├── pdf-extractext-documents
├── pdf-extractext-extractor
└── pdf-extractext-config
```

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build --wait
```

`--wait` termina cuando todos los servicios están sanos y los procesos de una sola vez
terminaron bien. Para apagar: `docker compose down` (con `-v` borra también los datos).

## Qué queda andando

| URL | Qué es |
|---|---|
| http://localhost/ | La interfaz (web) |
| http://localhost/api/health | Estado de web y de los servicios de los que depende |
| http://localhost/documents/ | API de documents |
| http://localhost/extractor/extract | API del extractor |
| http://localhost/config/ | API de config |
| http://consul.localhost/ | Interfaz de Consul |
| http://localhost:8080/ o http://traefik.localhost/ | Panel de Traefik: rutas, servicios y réplicas |

Traefik quita el prefijo antes de reenviar, así que ningún servicio sabe que existe.

## Arquitectura

```
                          http://localhost
                                 │
                   Traefik :80 · rate limit y retry
        ┌──────────────┬─────────┴─────┬────────────────┐
   /documents     /extractor        /config         / (el resto)
        ▼              ▼                ▼                ▼
    documents     extractor ×5       config             web: interfaz y orquestador
        │              ▲                │                │
     MongoDB           │          Consul (KV)            │ a documents y config llama
                       │                                 │ directo por la red interna
                       └──── Traefik :8081 (interno) ◄───┘
```

Una subida entra a web, que valida el PDF, le pregunta a documents si el checksum ya
existe, lo manda al extractor por el entrypoint interno de Traefik (protegido por un
circuit breaker) y le pide a documents que guarde el resultado. El detalle está en
[`SPEC.md`](SPEC.md#flujo-de-una-subida) y el porqué de cada decisión, en los
[ADR](docs/adr/).

## Cómo está armado

- **Solo Traefik publica puertos** (80 y el panel en 8080). MongoDB y Consul no se ven
  desde la máquina.
- **web llega al extractor por un entrypoint interno de Traefik** (`traefik:8081`), que no
  se publica y balancea las 5 réplicas (ADR 0005).
- **Procesos de una sola vez** (factor XII):
  - `documents-indexes` crea el índice único de checksum antes de que arranque documents.
  - `config-seed` carga en Consul los valores iniciales de web. Si una clave ya existe no la
    toca, así un cambio hecho en caliente sobrevive a un reinicio.
- **Contenedores propios endurecidos**: `read_only`, `cap_drop: [ALL]`,
  `no-new-privileges`, usuario de UID 10001 (lo pone cada imagen) y `/tmp` en memoria.
- **Solo documents recibe las credenciales de MongoDB**; solo config habla con Consul.

## Variables

Todas están explicadas en [`.env.example`](.env.example). La única obligatoria es
`MONGO_ROOT_PASSWORD`.

## Comandos útiles

```bash
docker compose ps                         # estado; solo traefik muestra puertos
docker compose logs -f web                # logs de un servicio
docker compose logs config-seed           # qué claves cargó
docker compose up -d --scale extractor=3  # cambiar la cantidad de réplicas
```

## Pruebas

| Qué | Dónde | Cómo |
|---|---|---|
| Configuración de Traefik | [`tests/`](tests/) | `uv run --group dev pytest tests` (corre en la CI) |
| Extremo a extremo por Traefik: subida, duplicados, CRUD, circuit breaker, config caído, documents caído y `429` | [`e2e/`](e2e/) | Con el stack levantado: `uv run --group dev pytest e2e -m e2e` |
| Carga con k6 y Vegeta | [`load/`](load/) | Ver [`docs/informe-carga.md`](docs/informe-carga.md) |

Cada servicio tiene además sus tests unitarios y de integración, que corren en su CI.

## Los doce factores

| Factor | Cómo se cumple | Evidencia |
|---|---|---|
| **I. Código base** | Un repositorio por servicio y uno de despliegue. El monolito de la Etapa 1 está archivado con la etiqueta `monolito-v1`. Ningún servicio despliega a otro | [ADR 0001](docs/adr/0001-un-repositorio-por-servicio-y-monolito-archivado.md), [`SPEC.md`](SPEC.md#problemas-del-factor-i-que-resuelve-esta-versión) |
| **II. Dependencias** | Cada servicio declara sus dependencias en `pyproject.toml` y las fija en `uv.lock`. La imagen instala con `uv sync --frozen --no-dev` y la CI audita las de producción con `pip-audit` | {f("documents", "Dockerfile", "Dockerfile de documents")}, {f("documents", ".github/workflows/ci.yml", "CI de documents")} |
| **III. Configuración** | Variables de entorno leídas solo por `Settings`, con `.env.example` en cada repositorio. La configuración de web que cambia en caliente vive en Consul, detrás de config. `.env` no se versiona y no hay secretos en Consul | [`.env.example`](.env.example), {f("web", "app/core/settings.py", "Settings de web")}, {f("config", "README.md", "README de config")} |
| **IV. Servicios de respaldo** | MongoDB, Consul y los otros servicios se usan por URL (`MONGODB_URI`, `CONSUL_URL`, `DOCUMENTS_URL`, `EXTRACTOR_URL`, `CONFIG_URL`): cambiarlos es cambiar una variable | [`docker-compose.yml`](docker-compose.yml) |
| **V. Construcción, publicación y ejecución** | La CI construye la imagen en cada PR y, al fusionar en `main`, la publica en ghcr con `latest` y el hash del commit. El compose solo usa imágenes y no monta código | {f("web", ".github/workflows/ci.yml", "CI de web")}, [`docker-compose.yml`](docker-compose.yml) |
| **VI. Procesos** | Ningún servicio guarda datos entre pedidos fuera de MongoDB o Consul. web solo guarda en memoria una caché de 5 s de la configuración y el estado del circuit breaker, que se pierden al reiniciar sin perder datos. El PDF nunca se escribe a disco | {f("web", "README.md", "README de web")}, {f("extractor", "README.md", "README del extractor")} |
| **VII. Asignación de puertos** | Cada servicio levanta su propio servidor HTTP en el puerto de `PORT` | {f("documents", "app/core/config/settings.py", "Settings de documents")}, {f("documents", "Dockerfile", "Dockerfile de documents")} |
| **VIII. Concurrencia** | El extractor escala con réplicas (5 por defecto) y Traefik las balancea. Supera la referencia del profesor en k6 y Vegeta | [`docker-compose.yml`](docker-compose.yml), [`docs/informe-carga.md`](docs/informe-carga.md) |
| **IX. Desechabilidad** | Cada imagen declara un `HEALTHCHECK` y cada servicio cierra sus conexiones al apagarse. `docker compose up -d --wait` termina con todo sano, y los e2e apagan y vuelven a levantar servicios | {f("documents", "app/main.py", "lifespan de documents")}, [`e2e/test_resilience.py`](e2e/test_resilience.py), [`e2e/test_documents_caido.py`](e2e/test_documents_caido.py) |
| **X. Paridad entre desarrollo y producción** | Desarrollo y producción usan las mismas imágenes y las mismas versiones de MongoDB y Consul, también en la CI. `docker-compose.build.yml` solo agrega la construcción local | [`docker-compose.build.yml`](docker-compose.build.yml) |
| **XI. Logs** | Todos los servicios escriben sus logs como un flujo en la salida estándar, que recoge Docker (`docker compose logs`); ninguno escribe archivos de log. La URI de MongoDB se loguea con la contraseña enmascarada | {f("documents", "app/infrastructure/database/connection.py", "conexión de documents")} |
| **XII. Procesos de administración** | La creación del índice único (`documents-indexes`) y la carga inicial de la configuración (`config-seed`) corren como procesos de una sola vez, con la misma imagen que el servicio | {f("documents", "app/admin/create_indexes.py", "create_indexes.py")}, [`docker-compose.yml`](docker-compose.yml) |

## Seguridad

- Imágenes multi-stage, sin uv ni herramientas de construcción, que corren con el usuario
  `10001`.
- `read_only`, `cap_drop: [ALL]`, `no-new-privileges` y `/tmp` en memoria en los
  contenedores propios.
- MongoDB con usuario y contraseña; solo documents recibe las credenciales. MongoDB y
  Consul no publican puertos.
- La CI de cada servicio corre `pip-audit` sobre las dependencias y Trivy sobre la imagen,
  y no publica una imagen con vulnerabilidades altas o críticas que tengan arreglo. Las
  que no lo tienen están justificadas en el README de cada servicio.

## Documentación

| Documento | Qué tiene |
|---|---|
| [`SPEC.md`](SPEC.md) | Objetivo, arquitectura, contratos, tecnologías y criterios de éxito |
| [`docs/adr/`](docs/adr/) | Las decisiones de arquitectura y su porqué |
| [`docs/workflow.md`](docs/workflow.md) | Ramas, commits, pull requests y TDD |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Los términos del dominio |
| [`docs/informe-carga.md`](docs/informe-carga.md) | Pruebas de carga a través de Traefik |
| [`tasks/plan.md`](tasks/plan.md) | El plan de la migración, tarea por tarea |
