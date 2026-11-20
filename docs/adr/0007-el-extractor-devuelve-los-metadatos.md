# El extractor devuelve también los metadatos del PDF

documents leía los metadatos con pypdf después de que el extractor ya había abierto el
PDF: la extracción vivía en dos aplicaciones (problema del factor I) y el PDF se abría dos
veces. El extractor pasa a devolver `metadata` junto a `content` y `page_count`, y pypdf
sale del sistema, con sus 18 vulnerabilidades conocidas en la versión que usábamos.

## Consecuencias

Es un campo agregado: el contrato del TP de carga sigue igual. Requiere un pull request
en el repositorio del extractor.
