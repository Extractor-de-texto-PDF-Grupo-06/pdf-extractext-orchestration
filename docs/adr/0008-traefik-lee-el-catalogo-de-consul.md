# Traefik lee también el catálogo de Consul, donde config se registra solo

El profesor pidió que Traefik y Consul estén vinculados: el panel de Traefik tiene que
mostrar los dos providers, Docker y Consul. Traefik suma el provider Consul Catalog, y
config se registra en el catálogo al arrancar, con su health check y las etiquetas de
Traefik que arman su ruta. Al apagarse se da de baja. El resto de los servicios sigue con
labels de Docker.

## Opciones consideradas

- **Registrar config con un archivo de definición en Consul.** Sin código nuevo, pero el
  registro no sigue a las réplicas: no se da de baja al apagarse ni registra una réplica
  nueva al escalar.
- **Registrar todos los servicios en Consul.** Más uniforme, pero obliga a tocar los
  cuatro servicios antes de la entrega, y el extractor tiene 5 réplicas que se tendrían
  que registrar cada una.
- **Que Traefik lea su configuración del KV de Consul** (provider Consul). Vincula las
  dos piezas, pero mezcla la configuración de rutas con la de los servicios.

## Consecuencias

- La ruta `/config` sale del catálogo de Consul (`config@consulcatalog` en el panel). Para
  que no haya dos routers para la misma ruta, config no lleva labels de Traefik.
- Las etiquetas las decide orchestration (`SERVICE_TAGS`), no el código de config: el
  servicio sigue sin saber cómo lo enruta Traefik.
- Los middlewares públicos siguen definidos en el provider Docker, así que la ruta de
  Consul los nombra con su sufijo: `public-rate-limit@docker`.
- Consul revisa `/health` de config cada 5 segundos y Traefik solo enruta a las réplicas
  sanas. Si una réplica muere sin darse de baja, Consul la borra al minuto.
- Si Consul no responde al arrancar, config arranca igual y solo se pierde la ruta pública:
  web llega a config directo por la red interna.
- Revisa en parte el ADR 0002, que descartaba el catálogo de Consul para esta versión, y
  el ADR 0003: el KV de Consul lo sigue usando solo config, pero Traefik ahora lee su
  catálogo.
