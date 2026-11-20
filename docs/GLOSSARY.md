# pdf-extractext

Sistema que recibe archivos PDF, extrae su texto y lo guarda para consultarlo y
editarlo después.

## Lenguaje

**Documento**:
El registro guardado de un PDF subido: su texto, checksum, nombre de archivo, cantidad de
páginas y metadatos. Nunca incluye el PDF original.
_Evitar_: archivo, PDF (cuando se habla de lo guardado), registro

**PDF**:
El archivo que sube el usuario. Vive solo en memoria mientras se procesa.
_Evitar_: documento (cuando se habla del archivo subido)

**Subida**:
La operación completa de recibir un PDF y, si es válido y nuevo, guardarlo como documento.
_Evitar_: carga, upload, ingesta

**Extracción**:
Obtener del PDF su texto, su cantidad de páginas y sus metadatos, sin guardar nada.
_Evitar_: procesamiento, parseo, análisis

**Texto**:
El contenido textual del PDF en Markdown, tal como lo devuelve la extracción.
_Evitar_: contenido, content (salvo como nombre de campo del contrato del extractor)

**Checksum**:
El hash SHA-256 del PDF en hexadecimal. Identifica al PDF por su contenido.
_Evitar_: hash, huella, firma

**Duplicado**:
Un PDF cuyo checksum ya corresponde a un documento guardado. No se guarda dos veces.
_Evitar_: repetido, copia

**Metadatos**:
Los datos que el propio PDF declara sobre sí mismo: autor, título, fechas de creación y
modificación.
_Evitar_: propiedades, info

**Firma PDF**:
Los bytes `%PDF` con los que empieza todo PDF válido.
_Evitar_: cabecera, magic number

## Configuración

**Configuración centralizada**:
Los valores que cambian el comportamiento de un servicio sin reconstruirlo, guardados en
el KV de Consul bajo `pdf-extractext/`. Nunca incluye secretos.
_Evitar_: settings remotos, parámetros

**Clave de configuración**:
El nombre de un valor de configuración centralizada, con la forma `<servicio>/<nombre>`.
_Evitar_: variable, propiedad
