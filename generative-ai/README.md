# Asistente analítico local

Implementado con Ollama y Qwen2.5 1.5B sobre CPU, sin API de pago. Herramientas
controladas consultan el DW; el modelo redacta una frase sin ejecutar SQL ni inventar
las cifras de la tabla. Se reconocen los casos sin información y se bloquean
explicaciones incompatibles con el respaldo. Evaluación real: 14 preguntas.

Inicio, contrato, controles y límites: [GENAI.md](GENAI.md).
