# Spec: pdf-extractext en microservicios — V1

Fecha: 19/11/2026 · Actualizada: 22/11/2026 · Entrega: miércoles 25/11/2026

## Objetivo

Migrar pdf-extractext del estado actual (un repositorio que mezcla documents-service con
el despliegue de todo el sistema) a microservicios, cada uno en su repositorio, con
**Traefik** como única puerta de entrada y **Consul** como configuración centralizada,
cumpliendo los doce factores de [The Twelve-Factor App](https://12factor.net/es/).

La funcionalidad no cambia respecto del monolito de la Etapa 1:

- Como usuario, subo un PDF y el sistema extrae **solamente su texto** y lo guarda junto
  con su checksum SHA-256, el nombre del archivo, la cantidad de páginas y sus metadatos.
- Como usuario, no puedo guardar dos veces el mismo PDF: el segundo intento responde 409.
- Como usuario, listo, veo, edito y borro los documentos guardados.
- El PDF nunca se escribe a disco, ni siquiera de forma temporal.

Motivo: el profesor marcó que **no se cumple el factor I** (código base). El diagnóstico
está en [Problemas del factor I](#problemas-del-factor-i-que-resuelve-esta-versión).

## Arquitectura

```
                   http://localhost                          http://consul.localhost
                           │                                          │
                       Traefik :80 ─────── panel :8080                │
        ┌──────────────┬───┴──────────┬───────────────┐               │
   /documents     /extractor       /config        / (el resto)        │
        │              │               │               │              │
    documents     extractor ×5      config ─────────── web ───────────┤
        │                              │          (interfaz y         │
     MongoDB                           └─────────► orquestador)   Consul (KV)
```

| Repositorio | Responsabilidad | Única dependencia | Datos propios |
|---|---|---|---|
| `pdf-extractext` | **El monolito de la Etapa 1**, archivado. Etiqueta `monolito-v1` | — | — |
| `pdf-extractext-orchestration` | Compose con Traefik, Consul y MongoDB; tests de extremo a extremo; documentación del sistema | Las imágenes de los servicios | — |
| `pdf-extractext-web` | Interfaz y orquestador (BFF). El navegador solo habla con él | documents, extractor, config | — |
| `pdf-extractext-documents` | CRUD de documentos | MongoDB (es el único que lo toca) | Colección `documents` |
| `pdf-extractext-extractor` | PDF → texto, cantidad de páginas y metadatos. Sin estado | PyMuPDF | — |
| `pdf-extractext-config` | CRUD de la configuración centralizada | Consul (es el único que lo toca) | KV bajo `pdf-extractext/` |

El compose de orchestration levanta además dos procesos de una sola vez (factor XII):
`documents-indexes` crea el índice único de checksum antes de que arranque documents, y
`config-seed` carga en Consul los valores iniciales de web sin pisar los que ya existen.

Todos los repositorios viven en la organización de GitHub
[`Extractor-de-texto-PDF-Grupo-06`](https://github.com/Extractor-de-texto-PDF-Grupo-06).
Las tareas se siguen como issues en un Project de la organización.

### Middlewares de Traefik

| Middleware | Dónde | Configuración |
|---|---|---|
| **Rate limit** | Rutas públicas (entrypoint `web`, puerto 80) | Promedio y ráfaga por IP de origen, configurables por `.env` (por defecto 100 y 200 por segundo). Al superarlo responde 429. El entrypoint interno que usa web para llegar al extractor no lo tiene, para no limitar las pruebas de carga |
| **Retry** | Rutas públicas y la interna del extractor | Hasta 3 intentos. Traefik solo reintenta cuando no pudo conectar con el servicio, así que un pedido que llegó a procesarse no se repite |

Los middlewares que comparten varias rutas (`public-rate-limit` y `public-retry`) se
definen en los labels del contenedor de **Traefik**, no en los de un servicio: Traefik
descarta los labels de un contenedor apagado o unhealthy, y si vivieran en documents, su
caída dejaría sin rutas a la interfaz, al extractor y a config. Un test de
orchestration lo verifica.

El circuit breaker no se configura en Traefik: vive en web (ver ADR 0004).

### Flujo de una subida

1. El navegador envía el PDF a web: `POST /api/documents` (multipart).
2. web valida extensión `.pdf`, MIME y tamaño, leyendo como máximo `límite + 1` bytes.
3. web calcula el checksum y le pregunta a documents si existe: `GET /?checksum=…`.
   Si existe, responde 409 sin llamar al extractor.
4. web envía el PDF al extractor **a través de Traefik**, protegido por el circuit breaker.
5. web le pide a documents que guarde: `POST /`. Si documents responde 409 (otra subida
   del mismo PDF llegó antes), web responde 409.
6. web responde 201 con el documento creado.

Si un paso falla, los siguientes no se ejecutan. Extraer no deja nada guardado, así que
no hay nada que deshacer (no hace falta Saga).

### Contratos HTTP

Traefik quita el prefijo antes de reenviar: ningún servicio sabe que existe.

**extractor** (sin cambios salvo el campo `metadata`; el contrato del TP de carga sigue
igual)

| Método y ruta | Entrada | Respuesta |
|---|---|---|
| `POST /extract` | Body binario `application/pdf` | `200` `{content, page_count, metadata}` · `413` · `422` · `503` saturado |
| `GET /health` | — | `200` |

**documents**

| Método y ruta | Entrada | Respuesta |
|---|---|---|
| `POST /` | JSON `{filename, checksum, text, page_count, metadata}` | `201` documento · `409` checksum repetido · `422` |
| `GET /?skip=&limit=` | — | `200` lista sin `text` |
| `GET /?checksum=` | — | `200` lista con 0 o 1 elemento |
| `GET /{id}` | — | `200` · `404` |
| `PUT /{id}` | JSON parcial `{filename?, text?, metadata?}` | `200` · `400` sin campos · `404` · `422` |
| `DELETE /{id}` | — | `204` · `404` |
| `GET /health` | — | `200` si MongoDB responde; `503` si no |

**config**

| Método y ruta | Entrada | Respuesta |
|---|---|---|
| `POST /` | JSON `{key, value}` | `201` · `409` ya existe · `422` |
| `GET /?prefix=` | — | `200` `{entries, total}` |
| `GET /{key}` | — | `200` · `404` |
| `PUT /{key}` | JSON `{value, index?}` | `200` · `404` · `409` si otro la cambió (check-and-set) |
| `DELETE /{key}` | — | `204` · `404` |
| `GET /health` | — | `200` si Consul tiene líder; `503` si no |

Claves: `<servicio>/<nombre>` en minúsculas (por ejemplo `web/max_file_size_mb`).
Valores: siempre texto. **Nunca secretos**: el KV de Consul guarda en texto plano.

**web**

| Método y ruta | Qué hace |
|---|---|
| `GET /` | La interfaz |
| `POST /api/documents` | El flujo de subida. `201` · `400` · `409` · `413` · `415` · `422` · `502` · `503` con `Retry-After` si el circuito está abierto |
| `GET /api/documents`, `GET/PUT/DELETE /api/documents/{id}` | Reenvía a documents |
| `GET /api/health` | Estado de web y de los servicios de los que depende |
| `GET /health` | `200` (vida del proceso, para Docker y Traefik) |

### Configuración centralizada

Solo la de web pasa por config: `web/max_file_size_mb`, `web/extractor_timeout_seconds`,
`web/circuit_breaker_failure_threshold` y `web/circuit_breaker_recovery_seconds`.

Se resuelve en dos niveles; gana el primero que exista:

1. Consul, a través de config. web la pide en cada subida, con una caché de 5 segundos,
   así un cambio vale sin reiniciar nada.
2. Las variables de entorno de web. Se usan si config no responde.

extractor y documents siguen configurándose solo por variables de entorno.

## Tecnologías

- Python 3.12, FastAPI y uv en todos los servicios
- PyMuPDF en extractor; Motor (MongoDB) en documents; `py-consul` en config; httpx en web
- MongoDB 9.0.4 con usuario y contraseña
- Consul 2.1 como servidor (`agent -server -bootstrap-expect=1 -client=0.0.0.0`), con
  volumen. Un agente sin `-server` no tiene líder y el KV no responde
- Traefik v3.6 con el proveedor Docker (`exposedbydefault=false`)
- Docker Compose v2; GitHub Actions; imágenes en `ghcr.io/extractor-de-texto-pdf-grupo-06/<repo>`

Las versiones exactas de las librerías las fija el `uv.lock` de cada repositorio.

## Comandos

En cada repositorio de servicio:

```bash
uv sync --group dev          # dependencias, incluidas las de desarrollo
uv run pytest                # tests unitarios: sin red, sin base, sin Consul
uv run pytest -m integration # tests contra el servicio real; se saltan si no está
uv run uvicorn app.main:app --reload
docker build -t <servicio>:dev .
```

En `pdf-extractext-orchestration`:

```bash
cp .env.example .env                                        # completar MONGO_ROOT_PASSWORD
docker compose up -d --wait                                 # con las imágenes de ghcr
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build --wait
                                                            # construye desde los repos clonados al lado
uv run pytest -m e2e                                        # tests de extremo a extremo por Traefik
```

## Estructura de los proyectos

Servicios nuevos (web y config):

```
app/
├── presentation/     routers y schemas de FastAPI
├── application/      casos de uso, puertos (interfaces) y entidades; solo biblioteca estándar
├── infrastructure/   adaptadores de los puertos: clientes HTTP, Consul, MongoDB
├── core/             Settings (variables de entorno)
├── dependencies.py   arma las dependencias
└── main.py
tests/
├── architecture.py, test_architecture.py   la regla de dependencias entre capas
└── test_*.py
```

documents y extractor conservan su estructura actual, que ya separa presentación, lógica
y datos. Renombrar sus carpetas al esquema anterior queda fuera de esta versión.

`pdf-extractext-orchestration`:

```
docker-compose.yml          producción: imágenes de ghcr
docker-compose.build.yml    desarrollo: construye desde ../pdf-extractext-*
.env.example
e2e/                        tests que entran por Traefik
docs/
├── GLOSSARY.md
├── adr/                    decisiones de arquitectura
└── workflow.md             ramas, commits, pull requests y TDD
SPEC.md
tasks/                      plan.md y todo.md
```

## Estilo de código

- Documentación, comentarios, mensajes de error y commits **en español**.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/es/):
  `tipo(alcance): descripción` en modo imperativo, menos de 72 caracteres.
- Errores HTTP siempre como `{"detail": "…"}`.
- Ningún módulo lee `os.environ`: toda la configuración pasa por `Settings`.
- Las dependencias se inyectan por constructor, para poder reemplazarlas en los tests.

```python
class UploadDocument:
    """Caso de uso: subir un PDF. Solo conoce puertos, no librerías."""

    def __init__(self, extractor: Extractor, documents: DocumentStore, config: ConfigSource):
        self._extractor = extractor
        self._documents = documents
        self._config = config
```

## Estrategia de pruebas

| Nivel | Dónde | Cuándo corre |
|---|---|---|
| Unitarios | `tests/` de cada servicio; adaptadores reemplazados por dobles o `httpx.MockTransport` | Siempre (`uv run pytest`) y en la CI de cada PR |
| Arquitectura | `tests/test_architecture.py` en web y config | Siempre |
| Integración | `@pytest.mark.integration`: contra MongoDB o Consul reales | A mano y en la CI cuando el servicio está disponible |
| Extremo a extremo | `pdf-extractext-orchestration/e2e`: entran por Traefik | Con el stack levantado |
| Carga | k6 y Vegeta del repositorio del extractor | Antes de la entrega |

### Integración continua

Cada repositorio de servicio tiene una CI con dos jobs, que la protección de ramas exige
en verde para fusionar:

| Job | Qué hace |
|---|---|
| `tests` | `uv sync --frozen` y todos los tests, incluidos los de integración contra el MongoDB o el Consul que levanta la CI |
| `docker` | Construye la imagen en cada pull request. Solo en un push a `main` la publica en ghcr con `latest` y el hash del commit |

orchestration valida el compose y corre los tests de los middlewares.

**TDD:** todo comportamiento nuevo empieza con un commit de tests en rojo y sigue con uno de
implementación en verde. Los valores esperados son literales, nunca la misma fórmula que
el código.

## Límites

- **Siempre:** correr los tests antes de cada commit; entrar por pull request hacia `develop`
  con la CI en verde (no hace falta aprobación de otro integrante); un tema por pull request; leer la
  configuración solo desde `Settings`; responder errores en el formato del contrato;
  conservar el historial al mover código entre repositorios.
- **Avisar al grupo:** cambiar un contrato HTTP, porque rompe a los servicios que lo usan
  (se actualiza la especificación en el mismo pull request); agregar una dependencia;
  transferir o archivar un repositorio.
- **Nunca:** escribir el PDF a disco; guardar secretos en Consul o en Git; escribir
  secretos en los logs (las URIs se loguean con la contraseña enmascarada); publicar puertos
  de MongoDB o Consul en la máquina; que un servicio hable con la base o con Consul de
  otro; copiar código de otros grupos de la cátedra; hacer push directo a `main`.

## Criterios de éxito

### Funcionales

- [ ] Subir un PDF válido desde `http://localhost` lo guarda con texto, checksum,
      cantidad de páginas y metadatos.
- [ ] Subir el mismo PDF otra vez responde 409, también si las dos subidas llegan a la vez.
- [ ] Listar, ver, editar y borrar funcionan desde la interfaz.
- [ ] Con el extractor apagado, la quinta subida fallida abre el circuito y la sexta
      responde 503 con `Retry-After` sin llamar al extractor.
- [ ] Cambiar `web/max_file_size_mb` en Consul cambia el límite sin reiniciar web.
- [ ] Superar el rate limit en una ruta pública responde 429; el entrypoint interno del
      extractor no tiene límite.
- [ ] Con config apagado, web sigue funcionando con sus variables de entorno.
- [ ] Con documents apagado, la interfaz, el extractor y config siguen respondiendo.

### Doce factores

- [ ] **I.** Cada repositorio contiene una sola aplicación. Ningún repositorio de servicio
      contiene código ni configuración de despliegue de otro. La copia vieja del extractor
      está archivada.
- [ ] **II.** Cada servicio instala con `uv sync --frozen --no-dev` desde su `uv.lock`; no
      hay `requirements.txt`.
- [ ] **III.** Toda la configuración entra por variables de entorno o por config; `.env`
      no está en Git y cada repositorio tiene `.env.example`.
- [ ] **IV.** MongoDB, Consul y los demás servicios se reemplazan cambiando una URL.
- [ ] **V.** La CI publica imágenes con el hash del commit; `docker-compose.yml` solo usa
      imágenes y no monta código.
- [ ] **VI.** Ningún servicio guarda estado entre pedidos fuera de MongoDB o Consul.
- [ ] **VII.** Cada servicio expone su propio servidor HTTP; el puerto se configura por
      `PORT`.
- [ ] **VIII.** El extractor escala a 5 réplicas y Traefik las balancea.
- [ ] **IX.** Todos los servicios tienen `HEALTHCHECK`, cierran sus conexiones al apagarse y
      `docker compose up -d --wait` termina con todo sano.
- [ ] **X.** Desarrollo y producción usan las mismas imágenes; el compose de desarrollo solo
      agrega la construcción local.
- [ ] **XI.** Los logs van a stdout; ningún servicio escribe archivos de log.
- [ ] **XII.** La creación del índice único de MongoDB y la carga inicial de la
      configuración corren como procesos de administración de una sola vez.

### Seguridad de Docker

- [ ] Todos los contenedores propios corren con un usuario sin privilegios de UID fijo
      (10001).
- [ ] Los Dockerfile son multi-stage: la imagen final tiene solo el entorno virtual y el
      código, sin uv ni herramientas de construcción, y declara un `HEALTHCHECK`.
- [ ] `read_only: true`, `cap_drop: [ALL]` y `no-new-privileges` en los contenedores
      propios, con `/tmp` en memoria.
- [ ] MongoDB con usuario y contraseña desde `.env`; solo documents recibe las credenciales.
- [ ] Solo Traefik publica puertos en la máquina.
- [ ] Sin vulnerabilidades conocidas de gravedad alta o crítica en las dependencias
      (`pip-audit`) ni en las imágenes (Trivy).

### Rendimiento

- [ ] Con k6 y Vegeta del TP, el extractor detrás de Traefik supera la referencia del
      profesor (25,35 req/s en k6; 16,65 req/s efectivos en Vegeta).

## Fuera de alcance (V2)

- Resúmenes con IA y exportación a `.docx`: la consigna no los pide.
- Message broker y comunicación asíncrona: el flujo no lo necesita y el contrato del TP es
  síncrono.
- Descubrimiento de servicios con Consul: Traefik los descubre por labels de Docker.
- Usuarios y autenticación (OAuth2): la consigna no pide usuarios.
- Logs centralizados y monitoreo más allá del panel de Traefik y los health checks.
- Renombrar las carpetas de documents y extractor al esquema de capas de los servicios nuevos.
- Kubernetes o cualquier despliegue fuera de Docker Compose.

## Problemas del factor I que resuelve esta versión

1. El extractor tenía dos códigos base: el de valendotjpg y una copia vieja en AugustoZz.
2. La extracción vivía en dos aplicaciones: documents conservaba el extractor de pypdf.
3. El repositorio de documents desplegaba el sistema completo (compose, nginx y Consul).
4. La configuración de nginx para el extractor estaba en dos repositorios.
5. `.test-extractor` proponía copiar el extractor dentro del repositorio de documents.

## Preguntas abiertas

Ninguna. El monolito restaurado (`5b38628`) se comprobó con `docker compose up` y quedó
archivado con la etiqueta `monolito-v1`.
