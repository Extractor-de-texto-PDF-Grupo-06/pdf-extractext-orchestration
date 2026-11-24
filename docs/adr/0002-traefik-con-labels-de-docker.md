# Traefik como única puerta de entrada, configurado con labels de Docker

Traefik reemplaza al nginx que balanceaba el extractor y pasa a ser la única puerta de
entrada: enruta por prefijo (`/documents`, `/extractor`, `/config`, el resto a web),
quita el prefijo antes de reenviar y es lo único que publica puertos. Descubre los
servicios por los labels de sus contenedores en el compose de orquestación, así que
ningún servicio sabe que Traefik existe.

## Opciones consideradas

- **Seguir con nginx.** Descartada: se configura a mano y resuelve las réplicas solo al
  arrancar. Lo pidió el profesor.
- **Traefik leyendo el catálogo de Consul.** Descartada para esta versión: obliga a que
  cada servicio se registre en Consul y suma una pieza que puede fallar. Se puede agregar
  después cambiando solo el proveedor de Traefik. *Revisado en el ADR 0008: Traefik suma
  el catálogo de Consul, donde se registra config.*

## Consecuencias

Traefik también aplica rate limit en las rutas públicas y retry cuando no puede conectar
con un servicio, configurados como middlewares en los mismos labels.

Traefik monta el socket de Docker en solo lectura para descubrir los contenedores. Es lo
habitual en local, pero le da acceso al demonio de Docker: no se usaría así en producción.
