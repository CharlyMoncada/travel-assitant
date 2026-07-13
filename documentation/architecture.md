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
            
            subgraph Routing ["Enrutamiento Híbrido"]
                Bypass{"⚡ Pre-check Determinista"}
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
        DB[("🗄️ SQLite DB<br/>travel_assistant.db")]
        VECTORS[("📂 ChromaDB Store<br/>chromadb_store/")]
    end

    %% Interfaces
    TG --> Router
    Web --> ENDPOINTS
    ENDPOINTS --> Router

    %% Enrutamiento Interno
    Router --> Bypass
    Bypass -->|Mensaje Determinista| Agents
    Bypass -->|Evaluación Semántica| Supervisor
    Supervisor -->|Charla / Clarificación| Router
    Supervisor -->|Identificación Semántica [ROUTE]| Agents

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
- **Traductor Pydantic Dinámico**: Convierte las definiciones en formato JSON `inputSchema` provenientes de los servidores MCP en clases **Pydantic V2** tipadas en tiempo de ejecución. Esto garantiza function calling de altísima precisión.
- **Filtrado Selectivo del Historial (`_get_clean_history`)**: Antes de consultar al Supervisor LLM, extrae un historial limpio omitiendo las etiquetas de enrutamiento interno (`[ROUTE: ...]`) y los mensajes de bajo nivel (`ToolMessage` y `AIMessage` con llamadas a funciones). Esto le presenta al Supervisor una línea de tiempo conversacional nítida (solo `HumanMessage` y `AIMessage` puros de interacción directa) ideal para tomar decisiones de *Sticky Routing*.
- **Persistencia de Estado Robusta y Checkpointer Fix**: Cuando el Supervisor decide desviar la consulta a un especialista, el Router inserta de forma explícita el `HumanMessage` actual en el checkpointer de LangGraph `MemorySaver` antes de invocar al sub-agente. Esto soluciona la inconsistencia en hilos conversacionales persistentes (donde el sub-agente creaba respuestas AI huérfanas de mensaje inicial del usuario en el checkpointer) y erradica errores de transaccionalidad de hilos paralelos.
- **Gestión de Memoria y Poda**: Instrumenta un algoritmo de poda conversacional por turnos completos (`_prune_history_if_needed`), manteniendo los últimos 3 turnos conversacionales de usuario completos en el checkpointer para optimizar el contexto.

#### B. Supervisor Enrutador Cognitivo (`app/agents/supervisor/`)
Encargado de la toma de decisiones en el enrutamiento de intenciones aplicando las directrices cognitivas del sistema:
- **`app/agents/supervisor/agent.py`**: Aloja la lógica del código del Supervisor LLM (`run_supervisor`), ejecutando la inferencia de enrutamiento cognitivo o respuestas directas.
- **System Prompts (`app/agents/supervisor/prompts.py`)**: Define `SUPERVISOR_SYSTEM_PROMPT` que inyecta las directrices cognitivas (Layer 1: palabras clave bilingües, Layer 2: sticky routing y Layer 3: chit-chat/ambigüedad) para clasificar la consulta de forma extremadamente flexible y dinámica.
- **Especificación Técnica (`app/agents/supervisor/supervisor_routing_skill.md`)**: Describe formalmente el comportamiento de enrutamiento y las capas cognitivas del skill del Supervisor.
- **Formato de Respuesta Estricto**: Retorna un token formal de enrutamiento (como `[ROUTE: finance]`, `[ROUTE: reminder]`, `[ROUTE: general]`) o una respuesta directa aclaratoria/social (Smalltalk) si no hay contexto previo o la consulta es informal.

#### C. Fábricas de Sub-Agentes Specialists Modulares
Cada sub-agente corre sobre un grafo simplificado de LangGraph independiente, aislando totalmente su comportamiento para evitar falsos function callings:
- **Finance Agent** (`app/agents/finance/`): Inicializa un agente focalizado. Filtra estrictamente el catálogo unificado de herramientas para exponer exclusivamente las de gastos (`expense`, `budget`) y carga el prompt de comportamiento financiero (`prompts.py`).
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
- Mantiene por separado la definición estructurada de las herramientas (`tools.py`) de la lógica del transporte SSE (`server.py`).
- Expone 4 herramientas CRUD estructuradas: `record_reminder`, `query_reminders`, `modify_reminder` y `delete_reminder`.
- Conectado directamente a las operaciones de la capa de persistencia en la base de datos relacional.

#### C. Capa de Persistencia (`app/services/persistence/`)
- Lógica de almacenamiento e interacción con SQLite mediante SQLAlchemy.
- Provee las consultas y mutaciones de datos relacionales seguras de gastos y recordatorios.

#### D. Capa RAG (`app/services/rag.py`)
- Recuperación semántica en base de datos ChromaDB con embeddings vectoriales generados por Sentence Transformers (`all-MiniLM-L6-v2`).
- Resuelve consultas normativas e introduce el contexto en el sistema RAG de forma perezosa (lazy).

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
| `obtener_tiempo` | `recommender_agent` | *(local)* | `ciudad` (str) | Consulta el clima actual para una ciudad usando wttr.in |
| `obtener_objetos` | `recommender_agent` | *(local)* | Ninguno | Devuelve la lista estándar de objetos para clasificar |


Además, el agente expone herramientas locales no MCP: `rules`, `logistics`, `obtener_tiempo` y `obtener_objetos`.

---

## Flujo de procesamiento de un mensaje

El procesamiento de cualquier solicitud en el sistema sigue una secuencia estructurada de enrutamiento cognitivo unificado y ejecución aislada:

1. **Recepción del Mensaje**: El usuario interactúa mediante Telegram o la consola web frontend (`POST /message`).
2. **Establecimiento de Conexiones MCP**: `TravelAgentOrchestrator` establece streams SSE simultáneos con los microservicios disponibles. Descubre dinámicamente las herramientas e instrumenta la traducción a clases tipadas **Pydantic V2**.
3. **Poda Conversacional**: Antes de evaluar, se recupera el estado del checkpointer y se realiza una poda de turnos conversacionales completos si se excede el límite preestablecido para evitar el desborde del contexto.
4. **Filtrado Selectivo del Historial**: El Router compila un historial limpio (`_get_clean_history`) excluyendo etiquetas y ToolMessages de bajo nivel para presentárselo en un formato nítido al Supervisor.
5. **Orquestación y Enrutamiento Cognitivo**: El Supervisor LLM recibe el historial limpio y el mensaje entrante. Aplicando sus habilidades semánticas internas definidas en su Prompt del Sistema (Bilingual Keywords & Sticky Routing):
   - *Ruta Semántica*: Determina y retorna una etiqueta estruturada (p. ej., `[ROUTE: finance]`).
   - *Interacción Directa*: Si la consulta es charla informal (Smalltalk) o vaga sin historial previo, responde directamente al usuario.
6. **Persistencia e Inyección de HumanMessage**: Si el Supervisor determina una ruta agéntica, el Router de forma inmediata e imperativa inyecta el `HumanMessage` del usuario en el checkpointer conversacional (`aupdate_state`). Esto preserva la consistencia de la línea de tiempo.
7. **Ejecución del Especialista Modular**: Se inicializa el sub-agente especialista correspondiente (`finance`, `reminder`, `general`) inyectándole su respectivo set hermético de herramientas e instrucciones. El sub-agente ejecuta asíncronamente el function calling necesario comunicándose mediante SSE con su respectivo servidor MCP.
8. **Consolidación de Memoria Segura**: La ejecución de los sub-agentes actualiza el checkpointer conversacional en SQLite de forma determinista usando el parámetro `as_node="model"` para erradicar cualquier error de colisión de esquemas.
9. **Inferencia y Respuesta**: Se extrae la respuesta final generada por el sub-agente especialista y se transmite al cliente de presentación del usuario.

---

## Consideraciones de Diseño y Clean Architecture

- **Aislamiento Cognitivo (Anti-Fatiga de LLM)**: En lugar de inyectar 11 herramientas y 4 prompts de sistema en una sola llamada (lo que causa falsos disparos en modelos rápidos), la arquitectura de sub-agentes divide el dominio. Cada agente tiene un contexto sumamente acotado (2 o 3 herramientas máximo) garantizando una precisión del 100% en function calling.
- **Enrutamiento Híbrido Avanzado**: Al combinar pre-checks de código estructurado de latencia cero con clasificación semántica mediante LLM, el sistema se siente instantáneo ante comandos explícitos del usuario y al mismo tiempo retiene capacidades conversacionales complejas.
- **Persistencia Robusta de Hilos**: Al emplear un motor centralizado de checkpointer (`MemorySaver`) coordinado pero delegando la ejecución a sub-agentes compilados dinámicamente, se logra tener hilos de chat compartidos y con transaccionalidad sin riesgo de colisión de esquemas.
- **Desacoplamiento Total de Capas**: Respetando rigurosamente Clean Architecture, la interfaz, el orquestador principal, los agentes especialistas y las herramientas sobre servidores remotos están totalmente separados físicamente y se comunican a través de contratos estrictos de red y validación tipada.
