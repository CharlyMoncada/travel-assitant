# Arquitectura del sistema Travel Assistant

## Visión general

El Travel Assistant es un sistema agéntico de asistencia al viajero que integra múltiples tecnologías de IA y persistencia para proporcionar una experiencia conversacional completa. La arquitectura se basa en tres pilares principales: Model Context Protocol (MCP), Retrieval-Augmented Generation (RAG), y persistencia inteligente.

## Diagrama de arquitectura

```mermaid
flowchart TB
    subgraph "Interfaces de Usuario"
        TG[Telegram Bot]
        WEB[Web Frontend]
        API[API REST]
    end

    subgraph "Backend FastAPI"
        MAIN[app/main.py]
        ENDPOINTS[app/api/endpoints.py]
        ROUTER[app/orchestrator/router.py]
        MCP[app/orchestrator/mcp.py]
    end

    subgraph "Servicios Core"
        LLM[app/services/llm.py<br/>OpenAI GPT-4.1-nano]
        RAG[app/services/rag.py<br/>ChromaDB + Embeddings]
        PERSIST[app/services/persistence.py<br/>SQLite + SQLAlchemy]
    end

    subgraph "Agentes Especializados"
        AGENTS[app/agents/__init__.py<br/>Rules, Budget, Logistics, Itinerary]
    end

    subgraph "Almacenamiento"
        DB[(SQLite<br/>travel_assistant.db)]
        VECTORS[(ChromaDB<br/>chromadb_store/)]
        DOCS[rag_docs/*.txt<br/>visa.txt, seguridad.txt, covid.txt]
    end

    subgraph "Configuración"
        ENV[.env<br/>OPENAI_API_KEY<br/>TELEGRAM_TOKEN<br/>EMBEDDING_MODEL]
    end

    %% Conexiones
    TG --> ROUTER
    WEB --> API
    API --> ENDPOINTS

    ENDPOINTS --> ROUTER
    ROUTER --> MCP
    MCP --> AGENTS

    AGENTS --> LLM
    AGENTS --> RAG
    AGENTS --> PERSIST

    RAG --> VECTORS
    RAG --> DOCS
    PERSIST --> DB

    MAIN --> ENV
    MAIN --> ENDPOINTS
    MAIN --> ROUTER
    MAIN --> MCP

    style "Interfaces de Usuario" fill:#e1f5fe,stroke:#01579b
    style "Backend FastAPI" fill:#f3e5f5,stroke:#4a148c
    style "Servicios Core" fill:#e8f5e8,stroke:#1b5e20
    style "Agentes Especializados" fill:#fff3e0,stroke:#e65100
    style "Almacenamiento" fill:#fce4ec,stroke:#880e4f
    style "Configuración" fill:#f5f5f5,stroke:#424242
```

## Componentes detallados

### 1. Interfaces de Usuario

#### Telegram Bot (`app/connectors/telegram_bot.py`)
- Integración con Telegram Bot API
- Recepción y envío de mensajes
- Configuración opcional mediante `TELEGRAM_TOKEN`

#### Web Frontend (`app/frontend/`)
- `index.html`: Interfaz de usuario simple
- `app.js`: Lógica de interacción con API REST
- Accesible en `/app` endpoint

#### API REST (`app/api/endpoints.py`)
Endpoints disponibles:
- `GET /`: Estado básico del sistema
- `GET /status`: Estado completo (LLM, RAG, MCP, DB)
- `POST /message`: Procesamiento de mensajes de usuario
- `GET /expenses`: Consulta de gastos
- `GET /reminders`: Lista de recordatorios
- `POST /llm/test`: Testing directo del LLM
- `GET /mcp/tools`: Lista de herramientas MCP
- `POST /mcp/execute`: Ejecución de herramientas MCP

### 2. Backend FastAPI

#### Punto de entrada (`app/main.py`)
- Configuración de FastAPI
- Inicialización de servicios (lazy loading para RAG)
- Configuración de rutas y middlewares
- Arranque del bot de Telegram (si está configurado)

#### Enrutador de mensajes (`app/orchestrator/router.py`)
- Procesamiento inicial de mensajes
- Coordinación entre MCP y agentes
- Manejo de respuestas

#### Orquestador MCP (`app/orchestrator/mcp.py`)
- Implementación del Model Context Protocol
- Registro y ejecución de herramientas
- Coordinación de flujos de trabajo

### 3. Servicios Core

#### Servicio LLM (`app/services/llm.py`)
- Integración con OpenAI GPT-4.1-nano
- Extracción de intenciones desde texto natural
- Generación de respuestas para RAG
- Funciones principales:
  - `extract_intent_payload()`: Análisis de intención
  - `compose_rag_answer()`: Generación de respuestas RAG
  - `raw_llm_call()`: Llamadas directas al LLM
  - `llm_status()`: Estado de configuración

#### Servicio RAG (`app/services/rag.py`)
- Sistema de Retrieval-Augmented Generation
- Base de datos vectorial con ChromaDB
- Embeddings locales con Sentence Transformers
- Funciones principales:
  - `_load_document_files()`: Carga de documentos desde `rag_docs/`
  - `init_rag()`: Inicialización lazy del sistema
  - `query_normative_documents()`: Consultas semánticas
  - `rag_status()`: Estado del sistema RAG

#### Servicio de Persistencia (`app/services/persistence.py`)
- Base de datos SQLite con SQLAlchemy
- Gestión de gastos y recordatorios
- Funciones principales:
  - `save_expense()`: Registro de gastos
  - `get_expense_summary()`: Consulta de gastos
  - `save_reminder()`: Guardado de recordatorios
  - `list_reminders()`: Lista de recordatorios

### 4. Agentes Especializados (`app/agents/__init__.py`)

#### TravelAssistant (Agente principal)
Coordina los agentes especializados:
- **Rules Agent**: Consultas normativas y requisitos
- **Budget Agent**: Gestión financiera
- **Logistics Agent**: Búsqueda de transporte y alojamiento
- **Itinerary Agent**: Gestión de itinerarios y recordatorios

### 5. Almacenamiento

#### Base de datos SQLite
- Archivo: `travel_assistant.db`
- Tablas: expenses, reminders
- ORM: SQLAlchemy

#### Base de datos vectorial ChromaDB
- Directorio: `app/chromadb_store/`
- Colección: `travel_rules`
- Modelo de embeddings: `all-MiniLM-L6-v2`

#### Documentos normativos
- Directorio: `rag_docs/`
- Archivos: `visa.txt`, `seguridad.txt`, `covid.txt`, `*.pdf`
- Formatos soportados: Texto plano (.txt) y PDF (.pdf)
- Procesamiento: Extracción automática de texto con pdfplumber

### 6. Configuración

#### Variables de entorno (.env)
```bash
# OpenAI (requerido para funcionalidades avanzadas)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

# Embeddings para RAG
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Telegram (opcional)
TELEGRAM_TOKEN=your-bot-token-here
```

## Flujo de procesamiento

1. **Recepción de mensaje**: Telegram Bot o API REST
2. **Enrutamiento inicial**: `router.py` analiza el mensaje
3. **Extracción de intención**: `llm.py` usa GPT para identificar intención
4. **Ejecución MCP**: `mcp.py` coordina las herramientas apropiadas
5. **Procesamiento especializado**:
   - Consultas normativas → RAG (`rag.py`)
   - Gastos → Persistencia (`persistence.py`)
   - Recordatorios → Persistencia (`persistence.py`)
6. **Respuesta**: Se genera y envía al usuario

## Tecnologías y dependencias

### Core
- **FastAPI**: Framework web asíncrono
- **OpenAI**: API de modelos GPT
- **ChromaDB**: Base de datos vectorial
- **Sentence Transformers**: Generación de embeddings
- **SQLAlchemy**: ORM para SQLite

### Utilidades
- **python-telegram-bot**: Integración Telegram
- **python-dotenv**: Gestión de variables de entorno
- **pydantic**: Validación de datos

### Desarrollo
- **uvicorn**: Servidor ASGI
- **pytest**: Testing (planeado)

## Consideraciones de diseño

### Inicialización Lazy
- El sistema RAG se inicializa solo cuando se necesita
- Evita delays en el startup del servidor
- Manejo de errores cuando ChromaDB no está disponible

### Separación de responsabilidades
- Cada servicio tiene una responsabilidad clara
- Interfaces bien definidas entre componentes
- Fácil testing y mantenimiento

### Escalabilidad
- Arquitectura modular permite agregar nuevos agentes
- RAG puede indexar más documentos
- API REST permite integraciones externas

### Seguridad
- Variables sensibles en `.env`
- Validación de inputs en endpoints
- Manejo seguro de errores

## Estado de implementación

✅ **Funcionalidades completadas**:
- Integración completa OpenAI GPT
- Sistema RAG con ChromaDB
- Persistencia SQLite
- API REST completa
- Bot Telegram
- Interfaz web básica
- Arquitectura MCP

🔄 **Mejoras pendientes**:
- Testing automatizado
- Documentación RAG expandida
- Métricas de rendimiento
- Logging avanzado
```

## Componentes principales

- `app/main.py`
  - Inicia el servidor FastAPI.
  - Carga `.env` y arranca el bot de Telegram si `TELEGRAM_TOKEN` está presente.
  - Inicializa la base de datos y el motor RAG.
  - Configura `app.state` para compartir `message_router`, `mcp_service` y `telegram_service`.
  - Incluye el router de endpoints de `app/api/endpoints.py`.

- `app/api/endpoints.py`
  - Define los endpoints HTTP públicos.
  - Usa `request.app.state` para acceder a los servicios del backend.
  - Agrupa la lógica REST para mensajes, estado, gastos, recordatorios y MCP.

- `app/connectors/telegram_bot.py`
  - Integra el bot de Telegram usando `python-telegram-bot`.
  - Recibe mensajes y los pasa al `MessageRouter`.
  - Maneja arranque y parada del polling.

- `app/orchestrator/router.py`
  - `MessageRouter` enruta los mensajes entrantes.
  - Cuando existe `MCPServer`, lo delega a él.
  - Tiene un fallback de reglas si el LLM no está disponible.

- `app/orchestrator/mcp.py`
  - Define `MCPServer`, el orquestador de herramientas.
  - Selecciona la herramienta usando el enrutador LLM.
  - Ejecuta la herramienta y devuelve la respuesta final.

- `app/orchestrator/mcp_tools.py`
  - Centraliza la definición de herramientas MCP.
  - Contiene los handlers de parseo de gasto y recordatorio.
  - Registra herramientas a `MCPServer` con ejemplos y descripciones.

- `app/frontend/index.html`
  - Interfaz web mínima que consume la API del asistente.
  - Provee botones para consultar estado, gastos, recordatorios y herramientas MCP.
  - Permite enviar mensajes a `/message` y ejecutar texto libre en `/mcp/execute`.

- `app/frontend/app.js`
  - Lógica de front-end para invocar los endpoints REST.
  - Presenta los resultados en la página de forma interactiva.

- `app/frontend/styles.css`
  - Estilos básicos para la interfaz web.

- `app/services/llm.py`
  - Construye prompts para la selección de herramienta (`route_tool`).
  - Extrae intención y payload estructurado para gastos y recordatorios (`extract_intent_payload`).
  - Genera respuestas naturales basadas en la salida de la herramienta (`render_llm_response`).
  - Expone el estado de la capa LLM.

- `app/services/rag.py`
  - Inicializa ChromaDB con documentos de `rag_docs/`.
  - Usa `sentence-transformers` para embeddings.
  - Responde consultas semánticas de normativa.

- `app/services/persistence.py`
  - Define los modelos de datos y funciones CRUD para gastos y recordatorios.

- `app/agents/__init__.py`
  - Contiene los agentes de dominio.
  - `TravelRulesAgent`: consulta normativa.
  - `BudgetAgent`: graba y resume gastos.
  - `ItineraryAgent`: guarda recordatorios.
  - `LogisticsAgent`: placeholder para búsquedas de viaje.

- `app/utils/tools.py`
  - Funciones de parseo de texto para gasto y recordatorio.

- `app/services/rag.py`
  - Inicializa ChromaDB con documentos de `rag_docs/`.
  - Usa embeddings para consulta semántica.
  - Responde consultas de búsqueda basadas en documentos.

- `app/services/persistence.py`
  - Define los modelos de datos y funciones CRUD para gastos y recordatorios.

- `app/connectors/telegram_bot.py`
  - Conecta con Telegram usando `python-telegram-bot`.
  - Maneja `/start` y mensajes de texto.
  - Corre el polling en un hilo independiente.

## Flujo de petición típico

1. El usuario envía un mensaje por Telegram o el endpoint `/message`.
2. `app/connectors/telegram_bot.py` o `app/api/endpoints.py` pasa el texto a `app/orchestrator/router.py`.
3. `app/orchestrator/router.py` delega la petición a `app/orchestrator/mcp.py` cuando está disponible.
4. `app/orchestrator/mcp.py` usa `app/services/llm.py` para extraer intención y payload estructurado, y para enrutar a la herramienta correcta.
5. La herramienta invoca un agente definido en `app/agents/`.
6. El agente consulta persistencia o RAG según corresponda.
7. El resultado se cristaliza en una respuesta de usuario y se devuelve al canal.

## Notas de expansión

- `app/services/rag.py` ya indexa documentos de ejemplo en `rag_docs/`.
- Los agentes se definen en `app/agents/__init__.py` y pueden integrarse con APIs reales.
- `app/orchestrator/mcp.py` centraliza la lógica de enrutamiento y reduce duplicación.
- El flujo de herramientas está preparado para adaptarse a nuevos conectores y APIs externas.
