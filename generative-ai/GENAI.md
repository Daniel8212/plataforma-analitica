# Asistente analítico local

Proveedor único: Ollama 0.40.16, `qwen2.5:1.5b` Q4_K_M, CPU, contexto 2048.
No necesita API de pago. Probado en el equipo: alrededor de 1,11 GB de memoria
del modelo y 3,94 s para la prueba técnica; la latencia varía con la pregunta.

## Inicio reproducible (PowerShell, raíz del repositorio)

```powershell
.\.venv\Scripts\python.exe deployment/prepare_ollama.py
.\deployment\start-ollama.ps1
```

En otra terminal, la primera vez:

```powershell
& .\data\tools\ollama-v0.40.16\ollama.exe pull qwen2.5:1.5b
.\.venv\Scripts\python.exe -m deployment.bootstrap
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Ollama escucha solamente en 127.0.0.1:11434. Modelo y binarios están ignorados en
`data/`; la descarga requiere Internet y aproximadamente 1 GB para el modelo.
El preparador descarga entradas CPU del ZIP oficial, valida CRC y registra SHA256
local; no afirma haber validado el hash del ZIP completo. Ollama verifica el modelo.
Su runtime puede crear su identidad estándar en `%USERPROFILE%/.ollama`; no es
parte del repositorio. Detener las terminales con Ctrl+C; no se instala un servicio.

Crear `APP_USER`/`APP_PASSWORD` locales según `.env.example`, con contraseña robusta.
Bootstrap crea una cuenta de eventos que solo inserta auditoría del chat; el lector
de métricas mantiene SELECT sobre vistas aprobadas. Nunca usar `sa` para atender chat.

## Contrato y límites

`POST /api/chat`, `X-API-Key`, cuerpo `{"question":"Ventas de marzo de 2016"}`.
Máximo 500 caracteres, doce solicitudes/minuto/IP, una generación concurrente.
503 si Ollama está apagado/ocupado; 429 si se supera la frecuencia. No hay fallback
externo ni cargos automáticos. La interfaz muestra errores y permite reintentar.

Un enrutador determinista selecciona herramientas de ventas, unidades, facturas,
ticket, comparación, productos, categorías y predicciones ya persistidas. Las
consultas parametrizadas usan vistas aprobadas. Nunca se ejecuta SQL del usuario
o del modelo. Los períodos relativos se anclan al último dato del DW, no al reloj
actual: la muestra termina el 31 de mayo de 2016. Sin período se pide aclaración.
Fuera de cobertura, geografía no modelada o causas comerciales: se reconoce la
falta de información sin llamar al modelo. No admite conversación con memoria.

Ollama recibe conceptos y una afirmación derivada por código, sin pregunta cruda,
datos personales ni cifras. Redacta una frase breve y cita identificadores. Las
cifras, períodos, fuente y última carga se muestran aparte desde las herramientas.
Se revisan esquema, citas, cifras, dirección, causas y marcadores. Si una explicación
no pasa, se bloquea y se muestran solo los datos (`grounded_fallback`). Estos
controles reducen errores; no constituyen una prueba general de veracidad lingüística.

Auditoría: hash de pregunta, versión del modelo, herramienta, carga, duración,
respuesta y explicación cruda restringida; no se conserva la pregunta libre.
Los casos de evaluación sí incluyen preguntas predefinidas públicas para revisión.

## Evidencias

```powershell
.\.venv\Scripts\python.exe -m generative_ai.evaluate
.\.venv\Scripts\python.exe -m pytest tests/test_genai.py
node tests/chat-browser.mjs
```

`documentation/evidence/genai-evaluation.json` registra 14 preguntas, respaldo,
respuesta real y afirmaciones bloqueadas, incluidas tres sin datos suficientes.
Ventas de marzo y unidades de mayo se contrastan con consultas OLTP independientes.
`chat-browser.json` y capturas documentan React → API → Ollama → datos visibles.
