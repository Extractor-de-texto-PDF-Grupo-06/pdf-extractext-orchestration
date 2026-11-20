# Un repositorio por servicio y el monolito archivado aparte

El profesor marcó que no se cumplía el factor I: el repositorio `pdf-extractext` era a la
vez el código de documents y el despliegue de todo el sistema, y el extractor tenía dos
códigos base. Decidimos un repositorio por microservicio, uno de orquestación con el
compose y la documentación del sistema, y conservar `pdf-extractext` como **el monolito
de la Etapa 1**, restaurado al commit `5b38628`, etiquetado `monolito-v1` y archivado.
Así el antes y el después se pueden levantar y comparar.

## Opciones consideradas

- **Repositorio "portada" sin código, con el monolito solo en una etiqueta.** Es lo que
  hizo otro grupo de la cátedra. Descartada porque el monolito queda escondido y no se
  puede levantar sin conocer la etiqueta.
- **Monorepo con una carpeta por servicio.** Descartada: la consigna pide un repositorio
  por microservicio.

## Consecuencias

En la organización hay dos aplicaciones que hacen lo mismo. No viola el factor I porque
son aplicaciones distintas y el monolito no se despliega con el sistema, pero su README
debe dejar claro que está archivado.
