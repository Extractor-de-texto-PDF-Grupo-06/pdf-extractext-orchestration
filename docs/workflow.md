# Forma de trabajo

## Ramas

- `main`: lo entregado. Solo recibe fusiones desde `develop`.
- `develop`: la rama por defecto. Todo pull request apunta acá.
- Una rama por issue: `tipo/descripcion-corta` (por ejemplo `feat/config-crud`).

`main` y `develop` están protegidas: nadie hace push directo.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/es/), en español y en modo
imperativo, con menos de 72 caracteres en el título:

```
feat(web): orquestar la subida con el circuit breaker
fix(documents): devolver 409 si el checksum ya existe
test(config): cubrir el check-and-set del PUT
```

Tipos: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `ci`, `perf`.

## TDD

Cada comportamiento nuevo son dos commits como mínimo:

1. `test(...)`: los tests nuevos, **en rojo**.
2. `feat(...)` o `fix(...)`: la implementación mínima que los pone **en verde**.

Después, si hace falta, `refactor(...)` con los tests en verde. El historial muestra el
orden, y esa es la evidencia de TDD.

## Pull requests

- Uno por issue, con `Closes #N` en la descripción para que el Project lo mueva solo.
- Para fusionar alcanza con que **la CI pase**. La revisión es opcional.
- **Excepción:** un cambio de contrato entre servicios (una ruta, un campo o un código de
  respuesta nuevo) lo mira otro integrante antes de fusionar, porque es lo que rompe a
  otro servicio.
- La descripción dice qué cambia, por qué y cómo se probó.

Elegimos no exigir aprobación para esta entrega: con una sola persona aprobando, sus
propios pull requests quedaban bloqueados (GitHub no permite aprobar uno propio) y se
volvía un cuello de botella.

## Issues y Project

Cada tarea del plan es un issue en el repositorio que toca, con criterios de aceptación
como checklist. El Project **Migración a microservicios** de la organización los junta
en un tablero: Pendiente → En curso → En revisión → Hecho.
