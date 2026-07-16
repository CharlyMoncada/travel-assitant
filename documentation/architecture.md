# Arquitectura del sistema Travel Assistant

## Visión general

El Travel Assistant es un sistema agéntico de asistencia al viajero que integra múltiples tecnologías de IA y persistencia para proporcionar una experiencia conversacional completa. La arquitectura sigue los principios de **Clean Architecture**, separando la capa de presentación, orquestación, lógica de negocio y persistencia.

En esta iteración, el sistema se ha refactorizado a una **arquitectura de red multiserver MCP desacoplada**, donde el núcleo del agente opera como un cliente de múltiples microservicios remotos de herramientas que se comunican mediante Server-Sent Events (SSE).

---

## Diagrama de arquitectura del sistema

```mermaid
flowchart TB
    subgraph UI ["Interfaces de Usuario (Port 8000)"]
        TG["🤖 Telegram Bot"]
        Web["💻 Web Frontend"]
    end

    subgraph Backend ["Backend de Presentación y Orquestación (Port 8000)"]
        MAIN["app/main.py"]
        ENDPOINTS["app/api/endpoints.py"]
        
        subgraph Orchestration ["Capa de Agentes (app/agents/)"]
            Router["🛠️ TravelAgentOrchestrator<br/>(Sesiones MCP, Poda & Memoria)"]
            
            subgraph Safety ["Capa de Seguridad Global (guardrails_input.py / guardrails_output.py)"]
                InputG["🛡️ Global Input Guardrails<br/>(Idioma / Prompt Injection)"]
                OutputG["🛡️ Global Output Guardrails<br/>(Fugas / Tracebacks / Tokens)"]
            end
            
            subgraph Routing ["Enrutamiento Concurrente (supervisor/agent.py)"]
                Supervisor["🧠 Supervisor LLM<br/>(Inferencia Semántica & Chat)"]
            end
            
            subgraph Agents ["Sub-Agentes Especialistas Modulares"]
                FA["💰 Finance Agent<br/>(finance/agent.py)"]
                RA["⏰ Reminder Agent<br/>(reminder/agent.py)"]
                GA["📚 General Agent<br/>(general/agent.py)"]
                REC["🎒 Recommender Agent<br/>(recommender/agent.py)"]
            end
        end
    end

    subgraph Servers ["Servidores de Herramientas MCP (Transporte SSE)"]
        FM["🔌 Finance MCP Server<br/>Port 8002"]
        RM["🔌 Reminder MCP Server<br/>Port 8003"]
    end

    subgraph Services ["Capa de Servicios y Negocio"]
        RULES["Tools locales RAG<br/>app/agents/general/tools.py"]
        PERSIST["Persistencia de dominio<br/>app/services/persistence/"]
        RAG["app/services/rag.py<br/>ChromaDB + SentenceTransformers"]
        REC_TOOLS["Tools locales equipaje<br/>app/agents/recommender/tools.py"]
    end

    subgraph Storage ["Almacenamiento y Persistencia"]
        DB[("🗄️ SQLite DB<br/>data/travel_assistant.db")]
        VECTORS[("📂 ChromaDB Store<br/>chromadb_store/")]
    end

    %% Interfaces
    TG --> Router
    Web --> ENDPOINTS
    ENDPOINTS --> Router

    %% Enrutamiento y Seguridad
    Router --> InputG
    InputG -->|Mensaje Seguro| Supervisor
    Supervisor -->|Charla / Clarificación| OutputG
    Supervisor -->|Identificación Semántica [ROUTES]| Agents
    Agents --> OutputG
    OutputG --> Router

    %% Conexiones e Invocaciones MCP / Locales
    FA -->|Llamada SSE| FM
    RA -->|Llamada SSE| RM
    GA -->|Tools locales| RULES
    GA -->|Búsqueda Semántica| RAG
    REC -->|Tools locales| REC_TOOLS

    %% Negocio a Datos
    FM --> PERSIST
    RM --> PERSIST
    PERSIST --> DB
    RAG --> VECTORS
```

---

## Componentes detallados

### 1. Interfaces de Usuario

#### Telegram Bot (`app/connectors/telegram_bot.py`)
- Integración nativa con la API de bots de Telegram.
- Recibe mensajes del usuario, los pasa al orquestador asíncrono y retorna la respuesta procesada.
- Inicializado de forma segura solo si se detecta la variable `TELEGRAM_TOKEN`.
- **Mecanismo de Envío Fragmentado (Chunking)**: Incorpora un sistema automático de división para fragmentar respuestas mayores de 4000 caracteres, segmentándolas por saltos de línea (`\n`) o espacios y transmitiéndolas de manera sucesiva para prevenir caídas de la API por límite de longitud (`Message is too long`).

#### Web Frontend (`app/frontend/`)
- Panel interactivo simple y moderno con una consola de chat y gráficos de gastos en tiempo real.
- Consume los endpoints unificados de la capa de presentación.

---

### 2. Capa de Presentación (Puerto `8000`)

#### Punto de entrada (`app/main.py`)
- Instancia la aplicación FastAPI, monta el frontend en la ruta estática y arranca el bot de Telegram en el startup.
- Inicializa de forma centralizada al cliente multiserver `TravelAgentOrchestrator` y lo inyecta en el estado de la aplicación (`app.state.message_orchestrator`).

#### API REST (`app/api/endpoints.py`)
Expone **7 endpoints unificados** de cara a la interfaz y el dashboard del usuario:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check básico de la API. |
| `GET` | `/app` | Sirve el frontend web interactivo. |
| `POST` | `/message` | Canal único del usuario para comunicarse con el agente LangChain. |
| `GET` | `/expenses` | Datos agregados de gastos y presupuesto para el dashboard. |
| `GET` | `/reminders` | Lista ordenada de alertas de viaje guardadas en la BD. |
| `GET` | `/status` | Estado dinámico consolidado de RAG, Base de Datos, Telegram y ambos servidores MCP externos. |
| `GET` | `/mcp/tools` | Catálogo de herramientas agregadas obtenidas dinámicamente de ambos servidores externos. |

---

### 3. Capa de Orquestación y Agentes Especialistas (Multi-Agente)

La arquitectura del asistente se ha modularizado y segmentado en múltiples archivos físicos dentro de `app/agents/` bajo un patrón **Multi-Agente con Supervisor Enrutador Cognitivo Unificado**:

#### A. Orquestador y Cliente Multiserver (`app/agents/orchestrator.py`)
- **`TravelAgentOrchestrator`**: Actúa como el punto de contacto unificado del backend con la infraestructura de agentes y servidores de herramientas.
- **Cliente Multiserver MCP**: Usa `AsyncExitStack` para abrir dinámicamente conexiones de stream de eventos de servidor (SSE) con múltiples microservicios concurrentes (`finance_server` y `reminder_server`).
- **Traductor Pydantic Dinámico**: Convierte las definiciones en formato JSON `inputSchema` provenientes de los servidores MCP en clases **Pydantic V2** tipadas en tiempo de ejecución.
- **Caché TTL de Herramientas**: Implementa una política de expiración por tiempo (TTL de 5 minutos / 300 segundos) para almacenar en caché las herramientas de los servidores MCP y evitar peticiones innecesarias en cada mensaje.
- **Validación de Seguridad en Dos Direcciones (Global Guardrails)**:
  - *Entrada (Language & Prompt Injection)*: En la entrada de `handle_message`, valida que la consulta esté en inglés o español (`check_language`) y no intente ataques de inyección (`check_prompt_injection`).
  - *Salida (Output Integrity)*: Antes de responder, valida que el mensaje final no contenga trazas de error crudas, tokens de plantillas LLM o directrices internas del prompt (`check_output_integrity`).
- **Enrutamiento Múltiple Secuencial**: Permite la ejecución de múltiples sub-agentes especialistas en serie ante consultas que contengan múltiples intenciones (ej. registrar un gasto y preguntar un requisito de viaje). El orquestador acumula las respuestas y retorna una respuesta integrada.
- **Directivas de Enfoque Especialistas**: Con el fin de evitar duplicaciones y resúmenes cruzados redundantes, inyecta a cada agente (finance, reminder, recommender, general) directivas del sistema muy restrictivas obligándolos a reportar única y exclusivamente información correspondiente a sus herramientas y dominios.
- **Filtrado Selectivo del Historial (`_get_clean_history`)**: Antes de consultar al Supervisor LLM, extrae un historial limpio omitiendo los metadatos de enrutamiento y mensajes de bajo nivel.
- **Evitación de duplicados en el Supervisor**: Remueve el último mensaje de usuario guardado en el historial persistente antes de construir el prompt del Supervisor para evitar duplicar el mensaje actual con la plantilla de inyección de memoria.
- **Gestión de Memoria y Poda**: Instrumenta un algoritmo de poda conversacional por turnos completos (`_prune_history_if_needed`), manteniendo los últimos 3 turnos conversacionales de usuario completos en el checkpointer.

#### B. Supervisor Enrutador Cognitivo (`app/agents/supervisor/`)
Encargado de la toma de decisiones en el enrutamiento de intenciones aplicando las directrices cognitivas del sistema:
- **`app/agents/supervisor/agent.py`**: Aloja la lógica del código del Supervisor LLM (`run_supervisor`), ejecutando la inferencia de enrutamiento cognitivo o respuestas directas, soportando múltiples destinos (`routes: list[str]`).
- **System Prompts (`app/agents/supervisor/prompts.py`)**: Define las directrices cognitivas (Layer 1: palabras clave bilingües, Layer 2: sticky routing y Layer 3: chit-chat/ambigüedad) y las restricciones geográficas de normativas (Europa únicamente).
- **Especificación Técnica (`app/agents/supervisor/supervisor_routing_skill.md`)**: Describe formalmente el comportamiento de enrutamiento del skill del Supervisor.

#### C. Fábricas de Sub-Agentes Specialists Modulares
Cada sub-agente corre sobre un grafo simplificado de LangGraph independiente, aislando totalmente su comportamiento para evitar falsos function callings:
- **Finance Agent** (`app/agents/finance/`): Inicializa un agente financiero enfocado en herramientas CRUD de gastos (`expense`, `budget`).
- **Reminder Agent** (`app/agents/reminder/`): Inicializa el agente de itinerario, exponiendo única y exclusivamente las herramientas CRUD de recordatorios.
- **General Agent** (`app/agents/general/`): Emplea las herramientas locales de consulta documental (RAG) y logística local.
- **Recommender Agent** (`app/agents/recommender/`): Sugiere equipaje y clasifica objetos de viaje según el clima del destino (haciendo uso de wttr.in y el listado de objetos CSV).

---

### 4. Capa de Servidores MCP e Infraestructura

Organizados en el directorio modularizado **`app/mcp/`**:

#### A. Finance MCP Server (`app/mcp/finance/server.py` - Puerto `8002`)
- Servidor MCP oficial que corre de forma autónoma.
- Expone herramientas financieras especializadas: `record_expense`, `query_expenses`, `modify_expense`, `delete_expense` y `budget`.
- Conectado a los servicios de dominio a través de la fachada de negocio.

#### B. Reminder MCP Server (`app/mcp/reminder/server.py` & `app/mcp/reminder/tools.py` - Puerto `8003`)
- Servidor MCP oficial autónomo dedicado en exclusiva a la gestión de recordatorios e itinerario.
- Expone 4 herramientas CRUD estructuradas: `record_reminder`, `query_reminders`, `modify_reminder` y `delete_reminder`.

#### C. Capa de Persistencia (`app/services/persistence/`)
- Lógica de almacenamiento e interacción con SQLite mediante SQLAlchemy.

#### D. Capa RAG (`app/services/rag.py`)
- Recuperación semántica en base de datos ChromaDB con embeddings vectoriales generados por Sentence Transformers (`all-MiniLM-L6-v2`).
- **Restricción Europea Estricta**: Si la consulta no tiene coincidencia semántica en la base de datos (lo cual ocurre para destinos fuera de Europa, ya que solo se dispone de documentación europea), intercepta la petición y devuelve un mensaje de advertencia localizado indicando que solo ofrece soporte regulatorio para destinos de Europa.

---

### 5. Catálogo de Herramientas MCP Detallado

| Herramienta | Servidor | Puerto | Parámetro Esperado | Propósito de Negocio |
|-------------|----------|--------|---------------------|----------------------|
| `budget` | `finance_server` | 8002 | Ninguno | Obtiene el resumen total del presupuesto |
| `record_expense` | `finance_server` | 8002 | `amount` (float), `description` (str), `category` (str) | Registra un gasto nuevo estructurado |
| `query_expenses` | `finance_server` | 8002 | `category` (str) (opcional) | Lista los gastos con opción de filtrado |
| `modify_expense` | `finance_server` | 8002 | `id` (int), opcionales `amount`, `description`, `category` | Edita propiedades de un gasto registrado |
| `delete_expense` | `finance_server` | 8002 | `id` (int) | Borra físicamente un gasto de la base de datos |
| `record_reminder` | `reminder_server` | 8003 | `title` (str), `due_time` (str), `note` (str) opcional | Crea un recordatorio nuevo en el itinerario |
| `query_reminders` | `reminder_server` | 8003 | (ninguno) | Lista todos los recordatorios registrados |
| `modify_reminder` | `reminder_server` | 8003 | `id` (int), opcionales `title`, `due_time`, `note` | Edita propiedades de un recordatorio existente |
| `delete_reminder` | `reminder_server` | 8003 | `id` (int) | Borra permanentemente un recordatorio |

Además, el agente expone herramientas locales no MCP: `rules` (RAG normativo), `travel_search` (búsqueda web con Brave Search), `get_weather` (clima vía wttr.in) y `get_packing_items` (lista de objetos a clasificar).

---

### 6. Flujo de procesamiento de un mensaje

El procesamiento de cualquier solicitud en el sistema sigue una secuencia estructurada de enrutamiento cognitivo unificado y ejecución aislada:

1. **Recepción del Mensaje**: El usuario interactúa mediante Telegram o la consola web frontend (`POST /message`).
2. **Capa de Seguridad Global (Input Guardrails)**: Valida la inyección de prompts y el idioma de entrada.
3. **Descubrimiento MCP con Caché TTL**: Se consultan las herramientas de los servidores remotos empleando el caché temporal (TTL de 5 minutos).
4. **Filtrado Selectivo del Historial y Poda**: El Router compila un historial de chat limpio y recorta el contexto de ser necesario.
5. **Orquestación y Enrutamiento Cognitivo**: El Supervisor LLM clasifica el mensaje y determina la lista de destinos (`routes: list[str]`). Si es Smalltalk o requiere clarificación, responde directamente al usuario.
6. **Ejecución Concurrente Especialista**: Por cada ruta devuelta, el orquestador invoca de forma paralela/concurrente a los sub-agentes especialistas correspondientes (`finance`, `reminder`, `general`, `recommender`) utilizando `asyncio.gather()`, acelerando los tiempos de respuesta hasta en un 3x antes de acumular sus respuestas en una sola.
7. **Capa de Seguridad Global (Output Guardrails)**: Comprueba la integridad del texto compilado final antes de enviarlo.
8. **Inferencia y Respuesta**: Guarda el mensaje consolidado y lo transmite al cliente.
