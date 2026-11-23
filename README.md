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

**Con las imágenes publicadas en ghcr:**

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <usuario> --password-stdin
docker compose up -d --wait
```

Los paquetes de la organización pueden requerir autenticación. Si `docker compose pull`
responde `unauthorized`, iniciá sesión con un token que tenga `read:packages` y acceso a
los cuatro paquetes; no hace falta clonar los repositorios de los servicios.

Para verificar que `latest` está publicado y es accesible antes de levantar el sistema:

```bash
docker compose pull
docker compose up -d --wait
docker compose ps
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
