# Travel Assistant

## Descripción

Asistente inteligente de viaje basado en IA Generativa que integra Model Context Protocol (MCP), Retrieval-Augmented Generation (RAG) y persistencia de datos. Desarrollado como Trabajo Fin de Máster.

## Características principales

- **🤖 Integración completa con OpenAI GPT**: Uso de GPT-4.1-nano para extracción de intenciones y generación de respuestas
- **🔍 Sistema RAG avanzado**: Búsqueda semántica en documentos normativos usando ChromaDB y embeddings locales
- **💬 Interfaces múltiples**: Soporte para Telegram Bot y API REST
- **🛠️ Arquitectura MCP**: Protocolo estandarizado para ejecución de herramientas
- **💰 Gestión financiera**: Registro y consulta de gastos en lenguaje natural
- **⏰ Sistema de recordatorios**: Gestión temporal de eventos de viaje
- **🌐 Frontend web**: Interfaz simple para testing y demostración

## Arquitectura del sistema

### Componentes principales

- **Backend FastAPI**: Servidor principal con endpoints REST
- **Agentes especializados**: Rules, Logistics, Budget, Itinerary
- **Servicios core**:
  - `llm.py`: Integración con OpenAI para procesamiento inteligente
  - `rag.py`: Sistema de recuperación aumentada con ChromaDB
  - `persistence.py`: Base de datos SQLite con SQLAlchemy
- **Orquestador MCP**: Coordinación de herramientas y flujos de trabajo
- **Conectores**: Integración con Telegram y otras plataformas

### Base de datos y almacenamiento

- **SQLite**: Persistencia de gastos, recordatorios y estado del sistema
- **ChromaDB**: Base de datos vectorial para documentos RAG
- **Documentos normativos**: Archivos .txt en `rag_docs/` (visa, seguridad, covid)

## Instalación y configuración

### 1. Entorno virtual
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows
```

### 2. Dependencias
```bash
pip install -r requirements.txt
```

### 3. Variables de entorno
Crea un archivo `.env` en la raíz del proyecto:

```bash
# OpenAI (requerido para funcionalidades avanzadas)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Embeddings para RAG
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Telegram Bot (opcional)
TELEGRAM_TOKEN=your-telegram-bot-token-here
```

### 4. Documentos RAG
Los documentos normativos deben estar en `rag_docs/`:
- `visa.txt`: Requisitos de visados
- `seguridad.txt`: Alertas de seguridad
- `covid.txt`: Restricciones sanitarias
- `Documentos de viaje para nacionales de países no pertenecientes a la UE.pdf`: Documentación completa de viajes (PDF, 6 páginas)

**Formatos soportados**: Archivos `.txt` y `.pdf`

## Uso

### Inicio del servidor
```bash
uvicorn app.main:app --reload
```

El servidor estará disponible en `http://127.0.0.1:8000`

### Endpoints principales

#### Estado del sistema
```bash
curl http://127.0.0.1:8000/status
```

#### Gestión financiera
```bash
# Ver gastos
curl http://127.0.0.1:8000/expenses

# Registrar gasto
curl -X POST "http://127.0.0.1:8000/message" \
  -H "Content-Type: application/json" \
  -d '{"text":"Anota 50€ en hotel"}'
```

#### Sistema RAG
```bash
# Estado del RAG
curl http://127.0.0.1:8000/status | jq '.rag'

# Consulta normativa
curl -X POST "http://127.0.0.1:8000/message" \
  -H "Content-Type: application/json" \
  -d '{"text":"¿Qué necesito para viajar a España?"}'
```

#### Testing LLM
```bash
# Test directo del LLM
curl -X POST "http://127.0.0.1:8000/llm/test" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola, ¿cómo estás?"}'
```

#### Herramientas MCP
```bash
# Listar herramientas disponibles
curl http://127.0.0.1:8000/mcp/tools

# Ejecutar herramienta
curl -X POST "http://127.0.0.1:8000/mcp/execute" \
  -H "Content-Type: application/json" \
  -d '{"text":"Anota 25€ en transporte"}'
```

### Interfaz web
Abre `http://127.0.0.1:8000/app` en tu navegador para acceder a la interfaz de testing.

### Bot de Telegram
Si configuraste `TELEGRAM_TOKEN`, el bot responderá automáticamente a mensajes en Telegram.

## Estructura del proyecto

```
travel-assistant/
├── app/
│   ├── api/
│   │   └── endpoints.py          # Endpoints REST
│   ├── services/
│   │   ├── llm.py               # Integración OpenAI
│   │   ├── rag.py               # Sistema RAG con ChromaDB
│   │   └── persistence.py       # Base de datos SQLite
│   ├── orchestrator/
│   │   ├── router.py            # Enrutador de mensajes
│   │   └── mcp.py               # Orquestador MCP
│   ├── agents/
│   │   └── __init__.py          # Agentes especializados
│   ├── connectors/
│   │   └── telegram_bot.py      # Bot de Telegram
│   ├── frontend/
│   │   ├── index.html           # Interfaz web
│   │   └── app.js               # Lógica frontend
│   └── main.py                  # Punto de entrada FastAPI
├── rag_docs/                    # Documentos para RAG
│   ├── visa.txt
│   ├── seguridad.txt
│   └── covid.txt
├── documentation/               # Documentación
├── .env                         # Variables de entorno
├── requirements.txt             # Dependencias Python
└── README.md
```

## Tecnologías utilizadas

- **Backend**: FastAPI, Python 3.13
- **IA**: OpenAI GPT-4.1-nano, Sentence Transformers
- **Base de datos**: SQLite + SQLAlchemy, ChromaDB
- **Mensajería**: python-telegram-bot
- **Frontend**: HTML5, JavaScript (vanilla)
- **Documentación**: Markdown, Mermaid diagrams

## Desarrollo y testing

### Testing del LLM
```bash
# Verificar configuración
python -c "from app.services.llm import llm_status; print(llm_status())"

# Test de intención
python -c "
from app.services.llm import extract_intent_payload
result = extract_intent_payload('Anota 30€ en comida')
print('Intent:', result)
"
```

### Testing del RAG
```bash
# Verificar estado
python -c "
from app.services.rag import rag_status
print('RAG Status:', rag_status())
"

# Test de consulta
python -c "
from app.services.rag import query_normative_documents
answer, sources = query_normative_documents('requisitos visa España')
print('Answer:', answer)
print('Sources:', len(sources))
"
```

### Base de datos
```bash
# Ver gastos
python -c "
from app.services.persistence import get_expense_summary
print(get_expense_summary())
"

# Ver recordatorios
python -c "
from app.services.persistence import list_reminders
print(list_reminders())
"
```

## Estado actual del proyecto

✅ **Completado**:
- Integración completa con OpenAI GPT
- Sistema RAG funcional con ChromaDB
- Endpoints REST completos
- Gestión de gastos y recordatorios
- Interfaz web básica
- Bot de Telegram
- Arquitectura MCP
- Persistencia con SQLite

🔄 **En desarrollo**:
- Mejoras en la precisión del RAG
- Expansión de documentos normativos
- Testing automatizado

## Contribución

Este proyecto es un Trabajo Fin de Máster. Para modificaciones, por favor contacta al autor.

## Licencia

Proyecto académico - Todos los derechos reservados.
- Comprueba que no hay errores de arranque en la consola.

### 2. Estado de la aplicación
- Ejecuta:
  ```bash
  curl http://127.0.0.1:8000/status
  ```
- Resultado esperado:
  - `telegram.enabled: true` si el token está configurado y el bot arrancó.
  - `rag.document_count` debe ser un número mayor o igual a 3.
  - `database.exists: true`.

### 3. Prueba del endpoint de mensajes REST
- Ejecuta:
  ```bash
  curl -X POST "http://127.0.0.1:8000/message" -H "Content-Type: application/json" -d '{"text":"Anota 20€ en transporte"}'
  ```
- Resultado esperado:
  - JSON con `message: "Gasto registrado"`.
  - El objeto `expense` debe contener `amount`, `category`, `description`.

### 4. Prueba de persistencia de gastos
- Ejecuta:
  ```bash
  curl http://127.0.0.1:8000/expenses
  ```
- Resultado esperado:
  - JSON con `total`, `count`, `by_category`, `items`.
  - El gasto registrado en el paso anterior debe aparecer en `items`.

### 5. Prueba de recordatorios
- Ejecuta:
  ```bash
  curl -X POST "http://127.0.0.1:8000/message" -H "Content-Type: application/json" -d '{"text":"Recuérdame check-in mañana 18:00"}'
  ```
- Ejecuta:
  ```bash
  curl http://127.0.0.1:8000/reminders
  ```
- Resultado esperado:
  - JSON con `reminders`.
  - El recordatorio creado debe aparecer en la lista.

### 6b. Prueba del enrutador LLM (opcional)
- Si configuraste `OPENAI_API_KEY`, envía mensajes más libres como:
  - `¿Puedo usar mi tarjeta de débito en Europa?`
  - `Recuérdame pagar el seguro de viaje el sábado`
- Resultado esperado:
  - El bot debe elegir la herramienta adecuada con mayor precisión.
  - Si LLM no está configurado, el sistema usa el enrutador local tradicional.

### 6. Prueba de RAG normativo
- Ejecuta:
  ```bash
  curl -X POST "http://127.0.0.1:8000/message" -H "Content-Type: application/json" -d '{"text":"Consulta requisitos de visa"}'
  ```
- Resultado esperado:
  - JSON con `answer` y `sources`.
  - `answer` debe incluir texto relevante de los documentos indexados.

### 7. Prueba del bot de Telegram
- En Telegram, abre `@testtravelassitant_bot`.
- Envía:
  - `/start`
  - `Anota 20€ en transporte`
  - `Recuérdame check-in mañana 18:00`
  - `Consulta requisitos de visa`
- Resultado esperado:
  - El bot responde en cada caso con mensajes coherentes.

### 8. Verificación de logs
- Revisa la salida de `uvicorn` para comprobar que no aparecen excepciones.
- Si hay errores, consulta el traceback y corrige antes de avanzar.

## Siguientes iteraciones

- Añadir conector real de WhatsApp.
- Integrar APIs de vuelo y alojamiento.
- Ampliar la colección RAG con más documentos oficiales.
- Implementar generación de respuestas más elaboradas aprovechando las fuentes.
- Añadir notificaciones y recordatorios programados.
