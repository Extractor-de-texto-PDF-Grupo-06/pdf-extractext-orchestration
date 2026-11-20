# Comunicación síncrona por HTTP, sin message broker

Los servicios se comunican por HTTP de pedido y respuesta. El usuario espera ver su
documento guardado al terminar la subida, y el contrato del TP de carga exige que el
extractor responda el texto en la misma llamada. Una cola (RabbitMQ o Kafka) agregaría
infraestructura, mensajes perdidos o duplicados y estados intermedios que el flujo no
necesita.

## Consecuencias

No hay transacciones distribuidas: la única escritura es la de documents, al final, y
extraer no deja nada guardado. Por eso no hace falta el patrón Saga.
