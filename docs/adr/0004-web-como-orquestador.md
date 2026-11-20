# web es la interfaz y el orquestador de la subida

El navegador solo habla con web, que sirve la interfaz y coordina la subida: valida el
archivo, calcula el checksum, pregunta a documents si es duplicado, llama al extractor y
le pide a documents que guarde. El circuit breaker hacia el extractor vive en web. Así
documents queda como un CRUD puro, dueño de MongoDB, sin saber que existe la extracción.

## Opciones consideradas

- **Un servicio de ingesta separado de la interfaz.** Descartado: es un servicio más sin
  responsabilidad propia que lo justifique.
- **El circuit breaker como middleware de Traefik.** Descartado: Traefik decide solo por
  la proporción de errores de red o de respuestas 5xx. El de web distingue un PDF inválido
  (422), que no es culpa del extractor, de una falla del extractor, y se escribió con TDD.
- **Que documents siga orquestando la subida.** Descartado: es lo que mezclaba la
  extracción con la persistencia.

## Consecuencias

La garantía contra duplicados sigue siendo el índice único de documents. La consulta
previa de web es solo un atajo para no extraer en vano.
