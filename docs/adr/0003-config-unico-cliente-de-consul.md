# El microservicio config es el único que habla con Consul

La configuración centralizada vive en el KV de Consul, pero ningún servicio usa Consul
directamente: config expone un CRUD por HTTP y es el único que conoce `py-consul`. Así
cambiar de almacén de configuración solo toca un servicio, y los demás no necesitan
librerías de Consul. Para que config no sea un punto único de falla, quien lo consulta
usa sus variables de entorno si no responde.

## Opciones consideradas

- **Cada servicio lee el KV de Consul al arrancar.** Era lo que hacía documents. Más
  simple, pero cada servicio queda acoplado a Consul y un cambio exige reiniciar.

## Consecuencias

Solo la configuración de web pasa por config. extractor y documents siguen solo con
variables de entorno: no tienen valores que haga falta cambiar en caliente.
