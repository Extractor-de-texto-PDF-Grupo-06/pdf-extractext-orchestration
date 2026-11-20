# web llama al extractor a través de Traefik, no por la red de Docker

Los servicios se hablan directo por la red interna de Docker, salvo web con el extractor:
lo llama a través de un entrypoint interno de Traefik, que no se publica en la máquina.
El extractor corre 5 réplicas, y el DNS de Docker no reparte bien la carga cuando el
cliente HTTP reutiliza conexiones; Traefik sí las balancea, que es el papel que antes
cumplía nginx.

## Consecuencias

Si Traefik se cae, web no puede extraer aunque las réplicas estén sanas. El circuit
breaker lo detecta como cualquier otro fallo del extractor.
