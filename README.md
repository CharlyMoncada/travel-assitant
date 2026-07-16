# Travel Assistant

## Descripción

Asistente inteligente de viaje basado en IA Generativa que integra una arquitectura multiserver del Model Context Protocol (MCP), Retrieval-Augmented Generation (RAG) y persistencia de datos relacionales en SQLite. Diseñado e implementado con una división clara bajo los principios de **Clean Architecture** como Trabajo Fin de Máster.

---

## Características principales

- **🤖 Arquitectura Multi-Agente con Supervisor**: Segmentación inteligente del comportamiento agéntico mediante un enrutador y sub-agentes especialistas en carpetas modulares para evitar la fatiga cognitiva del modelo en function calling masivos:
  - **Finance Agent** (`app/agents/finance/`): Focalizado en la gestión financiera con acceso exclusivo a herramientas del servidor de gastos.
  - **Reminder Agent** (`app/agents/reminder/`): Dedicado a la gestión del itinerario y recordatorios.
  - **General Agent** (`app/agents/general/`): Encargado de normativas de viajes (RAG) y logística local.
  - **Recommender Agent** (`app/agents/recommender/`): Recomendador inteligente de equipaje de viaje basado en ReAct prompting. Dado un destino, consulta el clima actual en tiempo real e infiere el tipo de destino (playa, montaña, urbano…) sin preguntar al usuario. Clasifica 62 objetos de viaje en tres categorías (✅ Obligatorios / 🟡 Recomendados / ❌ Descartados) y ofrece un consejo personalizado. Funciona como agente local puro (sin MCP), con sus propias herramientas async (`get_weather`, `get_packing_items`).
- **⚡ Enrutamiento Cognitivo Unificado**:
  - **Habilidad de Enrutamiento del Supervisor (Supervisor Skill)**: Inferencia inteligente conversacional que opera a nivel de directrices semánticas del Prompt de Sistema del Supervisor LLM, agrupado en tres capas cognitivas:
    - *Capa 1: Bilingual Keywords*: Identificación instantánea de intenciones en español e inglés utilizando un catálogo de palabras clave bilingües.
    - *Capa 2: Sticky Routing & Context Inheritance*: Hereda automáticamente el último dominio activo (gastos, recordatorios, general, equipaje) ante consultas conversacionales de seguimiento sin requerir aclaraciones adicionales.
    - *Capa 3: Restricción Reguladora a Europa*: Deniega el enrutamiento para consultas sobre visas o vacunas de países que no pertenecen a Europa, ya que los documentos cargados en el sistema solo cubren esta región.
  - **Enrutamiento Múltiple Secuencial (Multi-Intent)**: Capacidad para procesar mensajes con múltiples intenciones ejecutando secuencialmente los sub-agentes correspondientes (ej: guardar un gasto y consultar un requisito de viaje en una sola respuesta).
  - **Interacción Directa / Smalltalk**: Capacidad del Supervisor LLM para abordar saludos, despedidas o clarificar dudas ambiguas directamente sin enrutamiento agéntico cuando no hay contexto previo.
- **🔌 Arquitectura MCP Multiserver**:
  - **Finance MCP Server** (Puerto `8002`): Servidor independiente sobre SSE exclusivo para transacciones financieras CRUD de gastos.
  - **Reminder MCP Server** (Puerto `8003`): Servidor independiente sobre SSE exclusivo para la administración de recordatorios de viaje.
- **⚙️ Validación Pydantic Dinámica & Caché TTL**:
  - Conversión automática al vuelo de los esquemas de parámetros JSON (`inputSchema`) de múltiples servidores MCP remotos en modelos tipados **Pydantic V2** (`create_model`).
  - Almacenamiento temporal en caché (TTL de 5 minutos) de las herramientas MCP descubiertas para optimizar la latencia conversacional.
- **🛡️ Capa de Seguridad Global (Guardrails)** — 21 patrones de entrada + 5 checks de salida:
  - *Input Guardrails*: Detección de idioma (`check_language` para inglés y español) y bloqueo determinista por 21 expresiones regulares compiladas: anulación de instrucciones, cambio de rol, DAN/jailbreak, extracción de prompt, escalada de privilegios, exfiltración, bypass hipotético, many-shot jailbreak, token smuggling, simulation jailbreak, ofuscación base64 e inyección Markdown.
  - *Output Guardrails*: `check_output_integrity` intercepta: trazas Python, tokens de plantilla LLM, instrucciones de sistema filtradas, fugas de secrets/API keys y markup interno de tool calls.
- **💾 Persistencia e Integridad conversacional**: Persistencia estructurada de mensajes en SQLite (`data/travel_assistant.db`) con alineación de turnos (User-Assistant Symmetry) tolerante a fallos.
- **🧠 Memoria de usuario a largo plazo**: `ChatMemoryService` detecta preferencias declarativas del usuario (aeropuerto favorito, presupuesto, estilo de viaje) y las persiste por `thread_id` para recuperarlas en conversaciones futuras.
- **⚡ Sub-Agentes sin Estado (Stateless)**: Ejecución aislada y sin estado de sub-agentes (sin checkpointer interno), evitando contaminación de estado cruzado (cross-contamination) entre agentes y reduciendo drásticamente el consumo de tokens.
- **🔍 Sistema RAG avanzado**: Búsqueda semántica en documentos normativos (.txt y .pdf) usando ChromaDB y embeddings locales con inicialización lazy y fallback europeo integrado.
- **💬 Interfaces múltiples**: Punto de acceso único para frontend web y Bot de Telegram (opcional).

---

## Arquitectura del sistema

### Estructura Multiserver y Flujo de Decisiones Cognitivo

```mermaid
flowchart TB
    subgraph UI ["Interfaces de Usuario (Port 8000)"]
        TG["🤖 Telegram Bot"]
        Web["💻 Web Frontend"]
    end

    subgraph Backend ["Capa de Presentación y Orquestación (Port 8000)"]
        API[" FastAPI (POST /message)"]
        Router["🛠️ TravelAgentOrchestrator<br/>(Memoria, Conexión MCP, TTL & Guardrails)"]
        
        subgraph Routing ["Orquestación Cognitiva"]
            Supervisor["🧠 Supervisor LLM<br/>(Bilingual Keywords, Sticky Routing & Multi-intent)"]
        end
        
        subgraph Agents ["Sub-Agentes Especialistas Modulares"]
            FA["💰 Finance Agent<br/>(Prompt financiero + Tools de gastos)"]
            RA["⏰ Reminder Agent<br/>(Prompt recordatorios + Tools CRUD)"]
            GA["📚 General Agent<br/>(Prompt general + RAG & Local tools)"]
            REC["🎒 Recommender Agent<br/>(Prompt equipaje + wttr.in + CSV)"]
        end
    end

    subgraph Servers ["Servidores de Herramientas MCP Desacoplados"]
        FM["🔌 Finance MCP Server (Port 8002)"]
        RM["🔌 Reminder MCP Server (Port 8003)"]
    end

    subgraph Storage ["Servicios e Infraestructura"]
        DB[("🗄️ SQLite Database")]
        VectorDB[("📂 ChromaDB (RAG)")]
    end

    %% Flujo de entrada
    TG --> Router
    Web --> API
    API --> Router
    
    %% Flujo de Orquestación e Intención
    Router -->|1. Filtrar Historial conversacional limpio| Supervisor
    Supervisor -->|2a. Pequeña Charla o Aclaración Directa| Router
    Supervisor -->|2b. Identificar Ruta Semántica [ROUTES]| Router
    Router -->|3. Ejecución Secuencial| Agents

    %% Enlace a herramientas MCP remotas
    FA -->|Llamada SSE| FM
    RA -->|Llamada SSE| RM
    GA -->|Tools Locales / RAG| VectorDB
    REC -->|"get_weather (wttr.in)"| Internet(["🌐 wttr.in API"])
    REC -->|"get_packing_items (CSV)"| CSV(["📄 app/data/objetos.csv"])
    
    %% Acceso a Datos
    FM --> DB
    RM --> DB
    VectorDB --> DB
```

### Componentes de Software Principales

1. **Capa de Presentación** (Puerto `8000`):
   - `app/main.py`: Punto de entrada del backend y bot de Telegram.
   - `app/api/endpoints.py`: Expone los 7 endpoints REST unificados.
2. **Capa de Agentes y Orquestación** (`app/agents/`):
   - `app/agents/orchestrator/`: Paquete del orquestador (`__init__.py`, `orchestrator.py`, `mcp_client.py`, `agent_executor.py`, etc.). Administra la conexión asíncrona mediante `AsyncExitStack` y enruta subagentes concurrentemente.
   - `app/agents/orchestrator/guardrails_input.py` y `guardrails_output.py`: Capas unificadas de validación de entrada (idioma, prompt injection) y de integridad de salida.
   - `app/agents/supervisor/`: Contiene al Agente Supervisor y su lógica de enrutamiento cognitivo:
     - `app/agents/supervisor/agent.py`: Lógica del código de enrutamiento del Supervisor LLM (soporta enrutamiento múltiple).
     - `app/agents/supervisor/prompts.py`: Define el prompt cognitivo (`SUPERVISOR_SYSTEM_PROMPT`).
     - `app/agents/supervisor/supervisor_routing_skill.md`: Especificación técnica formal del skill de enrutamiento.
   - `app/agents/finance/`: Agente Especialista en Finanzas (`agent.py`, `prompts.py`, `finance_skill.md`).
   - `app/agents/reminder/`: Agente Especialista en Recordatorios (`agent.py`, `prompts.py`, `reminder_skill.md`).
   - `app/agents/general/`: Agente Especialista en Normas/Logística (`agent.py`, `prompts.py`, `tools.py`, `general_skill.md`).
   - `app/agents/recommender/`: Agente Recomendador de Equipaje (`agent.py`, `tools.py`, `prompts.py`, `recommender_skill.md`). Agente local puro sin MCP. Sus herramientas async en inglés (`get_weather` y `get_packing_items`) consultan `wttr.in` y el listado CSV.
   - `app/agents/general/tools.py`: Definiciones locales de herramientas del agente (`rules`, `travel_search`).
   - `app/data/objetos.csv`: Lista de 62 objetos de viaje clasificables (playa, montaña, frío, lluvia, generales) usada por el Recommender Agent.
3. **Capa de Infraestructura y Servidores MCP**:
   - `app/mcp/finance/server.py` (Puerto `8002`): Servidor MCP independiente sobre SSE exclusivo para la manipulación CRUD de transacciones financieras.
   - `app/mcp/reminder/server.py` (Puerto `8003`): Servidor MCP independiente sobre SSE exclusivo para la gestión CRUD de recordatorios e itinerario.
   - `app/services/persistence/`: Lógica CRUD de base de datos relacional para gastos y recordatorios.
   - `app/services/rag.py`: Lógica de embeddings semánticos y persistencia ChromaDB con interceptación de destinos fuera de Europa.

---

## Instalación y Configuración

### 1. Requisitos previos
Se recomienda el uso de Python 3.12 o superior en un entorno virtual aislado (Conda o venv).

### 2. Entorno virtual y dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows

# Instalar dependencias requeridas
pip install -r requirements.txt
```

### 3. Variables de entorno
Crea un archivo `.env` en la raíz del proyecto con la configuración de las APIs y parámetros del sistema:

```bash
# OpenAI (Requerido para inferencia avanzada y function calling)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-5-nano

# Embeddings RAG
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Configuración Multiserver del Agente (Separación por comas, opcional)
MCP_SERVERS=http://localhost:8002/sse,http://localhost:8003/sse
MCP_FINANCE_SERVER_STATUS_URL=http://localhost:8002/status
MCP_REMINDER_SERVER_STATUS_URL=http://localhost:8003/status

# Telegram Bot (Opcional, registrar con BotFather)
TELEGRAM_TOKEN=your-telegram-bot-token-here

# Monitoreo y Observabilidad (LangSmith - Opcional)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your-langsmith-api-key-here
LANGSMITH_PROJECT=travel-assistant

# Brave Search API (Requerido para la herramienta de búsqueda de vuelos/hoteles 'travel_search')
BRAVE_API_KEY=your-brave-api-key-here
BRAVE_SEARCH_COUNT=5
```

---

## 4. Estructura de datos persistentes

Todos los datos persistentes viven bajo `data/` (excluido de la imagen Docker):
```
data/
└── travel_assistant.db    # SQLite: gastos, recordatorios, conversaciones, memorias de usuario
```

El directorio `data/` se crea automáticamente al arrancar la aplicación. En Docker se monta como bind mount (`./data:/code/data`).

## 5. Docker y arranque conjunto
Se incluye `Dockerfile` y `docker-compose.yml` para lanzar los tres servicios en paralelo.

### Usar Docker Compose
```bash
# Crear el directorio de datos antes del primer arranque
mkdir -p data

docker compose up --build
```

---

## Ejecución del Sistema

El sistema opera con **tres procesos concurrentes** para asegurar el desacoplamiento físico de herramientas.

### Opción A — Script unificado (recomendado)

El script `start.sh` arranca los tres servicios en paralelo desde una única terminal, redirige los logs a `logs/` y los muestra en tiempo real. Presiona `Ctrl+C` para detener todos los procesos a la vez.

```bash
source .venv/bin/activate
./start.sh
```

---

### Opción B — Tres terminales independientes

#### 1. Iniciar el Servidor MCP de Finanzas (Puerto 8002)
```bash
python -m app.mcp.finance.server
```

#### 2. Iniciar el Servidor MCP de Recordatorios (Puerto 8003)
```bash
python -m app.mcp.reminder.server
```

#### 3. Iniciar el Backend Principal y Dashboard (Puerto 8000)
```bash
python -m app.main
```

---

## Catálogo de Herramientas Consolidadas (13 totales)

### 1. Servidor de Finanzas (`finance_server` - Puerto `8002` - MCP)

- `budget`: Obtiene el estado del presupuesto y el desglose de gastos acumulados.
- `record_expense`: Registra un nuevo gasto financiero. (Campos requeridos: `amount`, `description`, `category`).
- `query_expenses`: Consulta los gastos registrados.
- `modify_expense`: Modifica propiedades de un gasto por ID.
- `delete_expense`: Borra físicamente un gasto por ID único.

### 2. Servidor de Recordatorios (`reminder_server` - Puerto `8003` - MCP)

- `record_reminder`: Crea un nuevo recordatorio. (Campos requeridos: `title`, `due_time`).
- `query_reminders`: Lista recordatorios almacenados.
- `modify_reminder`: Modifica un recordatorio existente por ID.
- `delete_reminder`: Elimina un recordatorio por ID.

### 3. Agente Recomendador de Equipaje (`recommender_agent` - Local)

- `get_weather`: Consulta el clima actual para la ciudad de destino en tiempo real. (Campos requeridos: `city`).
- `get_packing_items`: Obtiene la lista completa de objetos por defecto a clasificar desde el archivo CSV local.

### 4. Agente General (`general_agent` - Local)

- `rules`: Realiza búsquedas semánticas (RAG) en los documentos normativos oficiales de viaje. (Campos requeridos: `text`).
- `travel_search`: Búsqueda en tiempo real de vuelos, hoteles y transportes mediante Brave Search.

---

## Pruebas Automatizadas (Unit/Integration Tests)

El sistema cuenta con una suite de pruebas consolidada en `scratch/test_suite.py` (17+ clases, 120+ tests) que valida:

| Área | Clases de test |
|------|---------------|
| Guardrails de idioma e inyección | `TestLanguageGuardrail`, `TestInjectionGuardrail`, `TestInjectionGuardrailExtended` |
| Guardrail de salida | `TestOutputIntegrityGuardrail`, `TestOutputIntegrityGuardrailExtended` |
| Prompts de agentes | `TestAgentFocusDirectives` |
| Telegram chunking | `TestTelegramResponseChunking` |
| Persistencia de gastos y recordatorios | `TestExpensePersistence`, `TestReminderPersistence` |
| Enrutamiento del supervisor | `TestSupervisorRouting` |
| Concurrencia del orquestador | `TestOrchestratorConcurrency` |
| Memoria a corto/largo plazo | `TestMemoryDetection`, `TestMemoryContextBuilder`, `TestDetectMemoryToSave`, `TestMemoryPersistence`, `TestConversationPersistence`, `TestChatMemoryServicePersistentHistory`, `TestBuildMemoryContext` |
| Brave Search | `TestBraveSearch`, `TestTravelSearchTool` |
| RAG | `TestRAGTextProcessing`, `TestRAGQueryLogic`, `TestRAGPDFExtraction`, `TestRAGStatus` |
| Recommender | `TestRecommenderWeatherTool`, `TestRecommenderPackingTool`, `TestRecommenderPrompt`, `TestRecommenderPackingItems` |

### Ejecución de Pruebas

Para ejecutar la suite completa de pruebas:
```bash
source .venv/bin/activate
python scratch/test_suite.py
```

Para correr únicamente un grupo o caso de prueba específico (por ejemplo, el enrutamiento del supervisor):
```bash
python -m unittest scratch/test_suite.py -k TestSupervisorRouting
```

---

## Protocolo de Pruebas E2E (Línea de Comandos)

### 1. Consultar el Estado del Asistente
```bash
curl http://localhost:8000/status
```

### 2. Registrar y Consultar un Gasto
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Anota un gasto de 45 euros en cena", "session_id": "test_e2e"}'
```

### 3. Consultas Normativas (RAG)
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "¿Cuáles son los requisitos de visa para viajar a España?", "session_id": "test_e2e"}'
```

### 4. Recomendador de Equipaje
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Ayúdame a hacer la maleta para un viaje de 5 días a Madrid", "session_id": "test_e2e"}'
```
