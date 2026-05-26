# Travel Assistant

## Descripción

Asistente inteligente de viaje basado en IA Generativa que integra una arquitectura multiserver del Model Context Protocol (MCP), Retrieval-Augmented Generation (RAG) y persistencia de datos relacionales en SQLite. Diseñado e implementado con una división clara bajo los principios de **Clean Architecture** como Trabajo Fin de Máster.

---

## Características principales

- **🤖 Arquitectura Multi-Agente con Supervisor**: Segmentación inteligente del comportamiento agéntico mediante un enrutador y sub-agentes especialistas en carpetas modulares para evitar la fatiga cognitiva del modelo en function calling masivos:
  - **Finance Agent** (`app/agents/finance/`): Focalizado en la gestión financiera con acceso exclusivo a herramientas del servidor de gastos.
  - **Reminder Agent** (`app/agents/reminder/`): Dedicado a la gestión del itinerario y recordatorios.
  - **General Agent** (`app/agents/general/`): Encargado de normativas de viajes (RAG) y logística local.
- **⚡ Enrutamiento Cognitivo Unificado**:
  - **Habilidad de Enrutamiento del Supervisor (Supervisor Skill)**: Inferencia inteligente conversacional que opera a nivel de directrices semánticas del Prompt de Sistema del Supervisor LLM, agrupado en dos capas cognitivas:
    - *Capa 1: Bilingual Keywords*: Identificación instantánea de intenciones en español e inglés utilizando un catálogo de palabras clave bilingües.
    - *Capa 2: Sticky Routing & Context Inheritance*: Inspección del historial conversacional limpio para heredar automáticamente el último dominio activo (gastos, recordatorios, general) ante consultas conversacionales de seguimiento del usuario (p. ej., "¿cuánto gasté en total?", "borrar", "ver lista") sin requerir aclaraciones adicionales.
  - **Interacción Directa / Smalltalk**: Capacidad del Supervisor LLM para abordar saludos, despedidas o clarificar dudas ambiguas directamente sin enrutamiento agéntico cuando no hay contexto previo.
- **🔌 Arquitectura MCP Multiserver**:
  - **Finance MCP Server** (Puerto `8002`): Servidor independiente sobre SSE exclusivo para transacciones financieras CRUD de gastos.
  - **Reminder MCP Server** (Puerto `8003`): Servidor independiente sobre SSE exclusivo para la administración de recordatorios de viaje.
- **⚙️ Validación Pydantic Dinámica**: Conversión automática al vuelo de los esquemas de parámetros JSON (`inputSchema`) de múltiples servidores MCP remotos en modelos tipados **Pydantic V2** (`create_model`), permitiendo que el LLM realice function calling robusto y seguro.
- **💾 Persistencia e Integridad conversacional**: Uso de LangGraph con `MemorySaver` resolviendo la ambigüedad en flujos complejos especificando de manera consistente la actualización de hilos mediante `as_node="model"`.
- **✂️ Poda dinámica del historial**: Limitación controlada a un máximo de 8 mensajes para mantener la ventana de contexto limpia de ruido y evitar alucinaciones.
- **🔍 Sistema RAG avanzado**: Búsqueda semántica en documentos normativos (.txt y .pdf) usando ChromaDB y embeddings locales (`all-MiniLM-L6-v2`) con inicialización lazy para optimizar el startup del servidor principal.
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
        Router["🛠️ LangChainAgentRouter<br/>(Memoria, Conexión MCP & Filtro Historial)"]
        
        subgraph Routing ["Orquestación Cognitiva"]
            Supervisor["🧠 Supervisor LLM<br/>(Bilingual Keywords & Sticky Routing)"]
        end
        
        subgraph Agents ["Sub-Agentes Especialistas Modulares"]
            FA["💰 Finance Agent<br/>(Prompt financiero + Tools de gastos)"]
            RA["⏰ Reminder Agent<br/>(Prompt recordatorios + Tools CRUD)"]
            GA["📚 General Agent<br/>(Prompt general + RAG & Local tools)"]
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
    Supervisor -->|2b. Identificar Ruta Semántica [ROUTE]| Router
    Router -->|3. Persistir HumanMessage en Checkpointer| Agents

    %% Enlace a herramientas MCP remotas
    FA -->|Llamada SSE| FM
    RA -->|Llamada SSE| RM
    GA -->|Tools Locales / RAG| VectorDB
    
    %% Acceso a Datos
    FM --> DB
    RM --> DB
    VectorDB --> DB
```

### Componentes de Software Principales

1. **Capa de Presentación** (Puerto `8000`):
   - `app/main.py`: Punto de entrada del backend y bot de Telegram.
   - `app/api/endpoints.py`: Expone los 7 endpoints REST unificados y el panel de control agregando el catálogo y estado de salud de todos los servidores MCP externos.
2. **Capa de Agentes y Orquestación** (`app/agents/`):
   - `app/agents/langchain_agent.py`: Orquestador y Router principal. Administra la conexión asíncrona a múltiples endpoints SSE mediante `AsyncExitStack`, realiza el filtrado selectivo del historial conversacional (`_get_clean_history`), maneja la traducción de esquemas MCP a Pydantic V2, realiza la poda periódica de mensajes, y persiste de forma explícita el mensaje del usuario antes de derivar al especialista.
   - `app/agents/supervisor/`: Contiene al Agente Supervisor y su lógica de enrutamiento cognitivo:
     - `app/agents/supervisor/agent.py`: Lógica del código de enrutamiento del Supervisor LLM.
     - `app/agents/supervisor/prompts.py`: Define el prompt cognitivo (`SUPERVISOR_SYSTEM_PROMPT`).
     - `app/agents/supervisor/supervisor_routing_skill.md`: Especificación técnica formal del skill de enrutamiento.
   - `app/agents/finance/`: Agente Especialista en Finanzas (`agent.py`) y sus prompts (`prompts.py`).
   - `app/agents/reminder/`: Agente Especialista en Recordatorios (`agent.py`) y sus prompts (`prompts.py`).
   - `app/agents/general/`: Agente Especialista en Normas/Logística (`agent.py`) y sus prompts (`prompts.py`).
   - `app/agents/prompts.py`: Repositorio común de system prompts (fallback).
   - `app/agents/tools.py`: Definiciones locales de herramientas del agente (`rules`, `logistics`).
3. **Capa de Infraestructura y Servidores MCP**:
   - `app/mcp/finance/server.py` (Puerto `8002`): Servidor MCP independiente sobre SSE exclusivo para la manipulación CRUD de transacciones financieras.
   - `app/mcp/reminder/server.py` (Puerto `8003`): Servidor MCP independiente sobre SSE exclusivo para la gestión CRUD de recordatorios e itinerario.
   - `app/services/persistence/`: Lógica CRUD de base de datos relacional para gastos y recordatorios.
   - `app/services/rag.py`: Lógica de embeddings semánticos y persistencia ChromaDB (lazy).

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
OPENAI_MODEL=gpt-4o-mini

# Embeddings RAG
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Configuración Multiserver del Agente (Separación por comas, opcional)
MCP_SERVERS=http://localhost:8002/sse,http://localhost:8003/sse
MCP_FINANCE_SERVER_STATUS_URL=http://localhost:8002/status
MCP_REMINDER_SERVER_STATUS_URL=http://localhost:8003/status

# Telegram Bot (Opcional, registrar con BotFather)
TELEGRAM_TOKEN=your-telegram-bot-token-here
```

> Nota: Si no se define `MCP_SERVERS`, el cliente multiserver usará por defecto `http://localhost:8002/sse` y `http://localhost:8003/sse`.

## 4. Docker y arranque conjunto
Se incluye `Dockerfile` y `docker-compose.yml` para lanzar los tres servicios en paralelo:
- backend principal (`web`) en el puerto `8000`
- servidor MCP de finanzas (`finance`) en el puerto `8002`
- servidor MCP de recordatorios (`reminder`) en el puerto `8003`

### Usar Docker Compose
```bash
docker compose up --build
```

### Detener los contenedores
```bash
docker compose down
```

### Volúmenes y persistencia
- La base de datos SQLite se monta desde el proyecto local como volumen.
- El store de ChromaDB también se monta para mantener el índice entre reinicios.

### Notas
- Asegúrate de tener `.env` en la raíz antes de levantar los servicios.
- Si deseas ejecutar solo un servicio, usa `docker compose run --rm <service>`.

### 5. Documentos normativos para RAG
Copia tus archivos oficiales o normativos en la carpeta `rag_docs/`:
- `visa.txt`: Políticas de visa y pasaportes.
- `seguridad.txt`: Normas y advertencias.
- `Documento_Viaje_UE.pdf`: Documentación oficial en PDF.

---

## Ejecución del Sistema

El sistema opera con **tres procesos concurrentes** para asegurar el desacoplamiento físico de herramientas:

### 1. Iniciar el Servidor MCP de Finanzas (Puerto 8002)
```bash
python -m app.mcp.finance.server
```

### 2. Iniciar el Servidor MCP de Recordatorios (Puerto 8003)
```bash
python -m app.mcp.reminder.server
```

### 3. Iniciar el Backend Principal y Dashboard (Puerto 8000)
```bash
python -m app.main
```

---

## Endpoints del Backend Principal (Puerto 8000)

El backend de presentación ofrece **7 endpoints de API unificados**:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check básico de la API |
| `GET` | `/app` | Sirve la interfaz interactiva web |
| `POST` | `/message` | Envío de mensajes del usuario para ser procesados por el agente LangChain |
| `GET` | `/expenses` | Obtiene el resumen total de gastos de la BD relacional |
| `GET` | `/reminders` | Obtiene el catálogo de recordatorios guardados en la BD |
| `GET` | `/status` | Estado dinámico de todos los módulos del sistema (servidores MCP 8002/8003, RAG, DB y Telegram) |
| `GET` | `/mcp/tools` | Catálogo consolidado de herramientas de los servidores externos |

---

## Catálogo de Herramientas MCP Consolidadas (9 totales)

### 1. Servidor de Finanzas (`finance_server` - Puerto `8002`)

- `record_expense`: Registra un nuevo gasto financiero. (Campos requeridos: `amount`, `description`, `category`).
- `query_expenses`: Consulta los gastos registrados con opción de filtrado. (Campos opcionales: `category`).
- `modify_expense`: Modifica propiedades de un gasto por ID. (Campos requeridos: `id`; opcionales: `amount`, `description`, `category`).
- `delete_expense`: Borra físicamente un gasto por ID único. (Campos requeridos: `id`).

### 2. Servidor de Recordatorios (`reminder_server` - Puerto `8003`)

- `record_reminder`: Crea un nuevo recordatorio. (Campos requeridos: `title`, `due_time`; `note` opcional).
- `query_reminders`: Lista recordatorios almacenados y permite filtrado.
- `modify_reminder`: Modifica un recordatorio existente por ID.
- `delete_reminder`: Elimina un recordatorio por ID.

---

## Protocolo de Pruebas E2E (Línea de Comandos)

Una vez que los servidores estén en ejecución, puedes validar las operaciones de la siguiente forma:

### 1. Consultar el Estado del Asistente
```bash
curl http://localhost:8000/status
```
*Debe retornar el estado `online` global e información individual de ambos servidores MCP.*

### 2. Crear y Manipular Gastos de Punta a Punta

- **Registrar un gasto nuevo** (Llama a `record_expense` en port 8002):
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Anota un gasto de 45 euros en cena", "session_id": "test_e2e"}'
```

- **Ver resumen presupuestario** (Llama a `budget` en el servidor de finanzas a través del agente):
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Muestra un resumen de mi presupuesto", "session_id": "test_e2e"}'
```

- **Modificar el gasto registrado** (Llama a `modify_expense` en port 8002):
```bash
# Asumiendo que el ID del gasto registrado fue 1
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Modifica el gasto con ID 1 para que el monto sea 50 euros y la categoría sea comida", "session_id": "test_e2e"}'
```

- **Borrar el gasto** (Llama a `delete_expense` en port 8002):
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Elimina el gasto con ID 1", "session_id": "test_e2e"}'
```

### 3. Consultas Normativas e Itinerario

- **Prueba RAG** (Llama a `rules` como herramienta local del agente):
```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "¿Cuáles son los requisitos de visa para viajar?", "session_id": "test_e2e"}'
```

---

## Interfaz Web
Abre `http://localhost:8000/app` en cualquier navegador web para interactuar de manera visual con la consola del chatbot y ver los gráficos de presupuesto agregados en tiempo real.

## Licencia
Proyecto académico de Trabajo Fin de Máster. Todos los derechos reservados.
