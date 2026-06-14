# Estado Actual y Cambios Recientes - Travel Assistant

## Resumen Ejecutivo

El Travel Assistant es un sistema agéntico de asistencia al viajero de última generación que integra IA generativa, RAG (Retrieval-Augmented Generation), persistencia relacional inteligente y una arquitectura de red modular multiserver Model Context Protocol (MCP). La arquitectura sigue rigurosamente los principios de **Clean Architecture**, dividiendo físicamente las herramientas y el núcleo conversacional en procesos desacoplados y consumidos dinámicamente mediante Server-Sent Events (SSE).

---

## Estado de Implementación

### ✅ Funcionalidades Completadas

#### 1. Integración OpenAI GPT
- **Modelo**: gpt-5-nano
- **Funcionalidades**:
  - Clasificación inteligente e invocación directa de herramientas asíncronas estructuradas.
  - Generación de respuestas contextuales enriquecidas por RAG.
  - Fallback controlado para errores de API del LLM.

#### 2. Sistema RAG Avanzado
- **Base de datos vectorial**: ChromaDB con almacenamiento persistente local en `app/chromadb_store/`.
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`).
- **Documentos**: Archivos normativos y de viaje (.txt y .pdf) en `rag_docs/`.
- **Características**:
  - Inicialización lazy para optimizar los tiempos de inicio del servidor principal.
  - Búsqueda de coincidencia semántica en documentos locales.
  - Respuesta fallback en texto cuando no hay documentos disponibles.

#### 3. Servidores MCP Oficiales Desacoplados
 1. **Finance MCP Server** (Puerto `8002`): Gestiona operaciones CRUD de gastos de manera aislada y robusta.
 2. **Reminder MCP Server** (Puerto `8003`): Gestiona recordatorios y tareas de viaje.
 **Transporte**: SSE (Server-Sent Events) sobre FastAPI.
 **Herramientas**: 9 herramientas estructuradas de dominio registradas con esquemas de parámetros JSON.

#### 4. Orquestación y Arquitectura Multi-Agente con Supervisor
- **Framework**: LangChain + LangGraph (con sub-agentes Stateless).
- **Patrón de Orquestación**: Arquitectura Multi-Agente basada en un Supervisor Central con Habilidades de Enrutamiento Cognitivo Unificado (`app/agents/supervisor/`) y sub-agentes modularizados especialistas sin estado, con inyección de historial y contexto desde SQLite.
  - **Finance Agent**: Aislado en `app/agents/finance/` con herramientas e instrucciones del dominio de gastos y finanzas.
  - **Reminder Agent**: Confinado en `app/agents/reminder/` exclusivamente a herramientas de creación, modificación y listado de recordatorios.
  - **General Agent**: Administra el flujo del RAG para normativas de viaje y soporte local desde `app/agents/general/`.
- **Enrutamiento Cognitivo Unificado (Supervisor Skill)**:
  - *Capa 1: Bilingual Keywords*: Identificación semántica inteligente de intenciones ante palabras clave bilingües de finanzas, recordatorios y normativas directamente en el prompt del sistema.
  - *Capa 2: Sticky Routing & Context Inheritance*: Herencia contextual automática del último dominio activo en el historial conversacional ante consultas breves o de continuación del usuario (p. ej., "borrar", "¿cuánto gasté?").
  - *Interacción Directa*: Capacidad del Supervisor para responder Smalltalk o clarificar dudas ambiguas directamente sin enrutamiento agéntico.
- **Conectividad y Robustez**: Uso de `AsyncExitStack` paraStreams SSE paralelos.
- **Validación Dinámica**: Mapeo robusto e instantáneo de catálogos MCP a Pydantic V2.
- **Salvedades de Persistencia y Memoria**: Persistencia de mensajes estructurada en SQLite con alineación de turnos (User-Assistant Symmetry) garantizada y tolerancia a fallos. Eliminación completa de la dependencia de checkpointers en sub-agentes para erradicar contaminaciones cruzadas y token overhead.

#### 5. Capa de Servicios de Dominio (Clean Architecture)
- La lógica de negocio principal está centralizada en los módulos de persistencia bajo `app/services/persistence/`.
- Las herramientas locales del agente (`rules` y `logistics`) se encuentran en `app/agents/tools.py`.
- No existe actualmente un archivo de servicios de dominio global como `TravelServices`; la arquitectura funciona con un router agnóstico que consume servicios MCP remotos.

#### 6. Persistencia de Datos
- **Base de datos**: SQLite local con SQLAlchemy ORM.
- **Entidades**: Gastos (`Expense`) y recordatorios (`Reminder`).
- **Operaciones**: CRUD completo (`save`, `get_summary`, `modify`, `delete`) con transacciones seguras.

#### 7. Interfaces de Usuario e Integraciones
- **API REST**: 7 endpoints unificados en el puerto `8000`.
- **Bot Telegram**: Integración opcional lista para producción mediante Token de Telegram.
- **Frontend Web**: Consola interactiva en HTML/JS con gráficos agregados en tiempo real.

#### 8. Monitoreo y Observabilidad (LangSmith)
- **Framework**: Integración nativa con la suite de observabilidad de LangSmith.
- **Características**:
  - Decoradores `@traceable` en las funciones críticas de `TravelAgentOrchestrator` (`_run_specialized_agent` y `handle_message`).
  - Monitoreo en tiempo real de flujos agénticos de decisión (enrutamiento de supervisor y ejecución de agentes específicos).
  - Trazabilidad de latencia, coste de tokens, llamadas al LLM e interacciones con herramientas.
  - Modo autocontenido pasivo (*no-op*) integrado: si no están presentes las credenciales correspondientes en el entorno, el código se ejecuta de forma habitual sin interrupciones.

---

### 🔄 Cambios Recientes (Refactorización Multiserver y Multi-Agente)

#### 1. Separación de Servidores MCP
- **Antes**: Un único servidor en el puerto 8001 que exponía herramientas pasivas.
- **Ahora**: Creación de una carpeta modular `app/mcp/` y división física de responsabilidades en subpaquetes dedicados:
  - `app/mcp/finance/server.py` y `app/mcp/finance/tools.py` en puerto `8002` (exclusivo para operaciones CRUD de gastos).
  - `app/mcp/reminder/server.py` y `app/mcp/reminder/tools.py` en puerto `8003` (exclusivo para operaciones CRUD de recordatorios).
- **Limpieza**: Eliminación del soporte legado y consolidación de los servidores MCP en subpaquetes dedicados.

#### 2. Transición a Arquitectura Multi-Agente Modularizada
- **Antes**: Sub-agentes planos (`finance_agent.py`, `reminder_agent.py`, `general_agent.py`, `supervisor_agent.py`) en la raíz de `app/agents/` compartiendo un `prompts.py` centralizado.
- **Ahora**: Modularización física por agente en subdirectorios individuales dentro de `app/agents/`:
  - `app/agents/supervisor/`: Agente Supervisor con su lógica `agent.py`, prompts de enrutamiento `prompts.py` y especificación técnica `supervisor_routing_skill.md`.
  - `app/agents/finance/`: Sub-agente financiero con su constructor `agent.py` y prompts dedicados.
  - `app/agents/reminder/`: Sub-agente de recordatorios con su constructor `agent.py` y prompts dedicados.
  - `app/agents/general/`: Sub-agente general con su constructor `agent.py` y prompts dedicados.
  - **Limpieza de Fallback**: Eliminación completa de `app/agents/prompts.py` (antiguo prompt general de fallback), delegando toda petición de ruta no reconocida directamente al agente `general` de forma robusta.

#### 3. Estabilidad y Gestión de Memoria Stateless
- **Conversión a Sub-agentes Stateless**: Los sub-agentes se ejecutan sin checkpointers y sin estado compartido, eliminando la duplicación del historial, la sobrecarga de tokens por llamadas internas a herramientas MCP pasadas, y la contaminación de estado cruzado.
- **Distribución de Herramientas desde el Orquestador**: Las herramientas dinámicas descubiertas de servidores MCP se asocian a su URL/Puerto de origen y se distribuyen selectivamente a cada sub-agente, desacoplándolos de lógica de filtrado dura.
- **Contexto Global de Fechas**: Inyección de un resolver dinámico de fechas relativas (`app/utils/date_resolution.py`) en recordatorios y finanzas, permitiendo que ambos interpreten adecuadamente expresiones como "ayer", "este viernes", etc.
- **Robustez de Errores con ToolException**: Implementación de excepciones estructuradas (`ToolException`) con captura controlada (`handle_tool_error=True`) en todas las herramientas MCP para informar de forma segura al LLM sobre caídas de red o fallos de transacciones.
- **Garantía de Turnos en BD**: Guardado temprano de mensajes del usuario para asegurar la integridad de la base de datos de chats en SQLite frente a excepciones durante el flujo de ejecución.

#### 4. Unificación en el Backend de Presentación
- El endpoint `/status` se actualizó para interrogar concurrentemente a los servidores de herramientas MCP en sus respectivos puertos, calculando la disponibilidad del sistema de forma global y agregada.
- El catálogo de herramientas expuesto en `/mcp/tools` se consolida dinámicamente consultando los servidores disponibles, garantizando la retrocompatibilidad con el panel web frontend.

---

### 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Endpoints REST de Presentación (Port 8000) | 7 |
| Servidores MCP Independientes | 2 (Puertos 8002 y 8003) |
| Herramientas MCP Totales | 9 remotas + 2 locales |
| Servicios de Dominio | 4 (+ fachada) |
| Validación de Parámetros | Pydantic V2 Dinámico |
| Cobertura RAG | Documentos TXT y PDF unificados |
| Observabilidad y Monitoreo | Integración nativa con LangSmith |

---

## Arquitectura del Proyecto

### Estructura de Directorios

```
travel-assistant/
├── app/
│   ├── main.py                         # FastAPI App principal en puerto 8000
│   ├── api/
│   │   └── endpoints.py                # 7 endpoints unificados
│   ├── agents/                         # Módulo de agentes y orquestación
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # Cliente Multiserver asíncrono con Pydantic y persistencia
│   │   ├── tools.py                    # Herramientas locales del agente (rules, logistics)
│   │   ├── supervisor/                 # Agente Supervisor y Enrutador Cognitivo
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica del Supervisor (Código de Enrutamiento)
│   │   │   ├── prompts.py              # Prompts específicos del Supervisor (SUPERVISOR_SYSTEM_PROMPT)
│   │   │   └── supervisor_routing_skill.md  # Especificación del Skill
│   │   ├── finance/                    # Agente Especialista en Finanzas
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica de construcción del sub-agente
│   │   │   └── prompts.py              # FINANCE_AGENT_SYSTEM_PROMPT
│   │   ├── reminder/                   # Agente Especialista en Recordatorios
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica de construcción del sub-agente
│   │   │   ├── prompts.py              # REMINDER_AGENT_SYSTEM_PROMPT
│   │   │   └── reminder_skill.md       # Especificación del Skill de Recordatorios
│   │   └── general/                    # Agente Especialista en RAG y Logística
│   │       ├── __init__.py
│   │       ├── agent.py                # Lógica de construcción del sub-agente
│   │       └── prompts.py              # GENERAL_AGENT_SYSTEM_PROMPT
│   ├── connectors/
│   │   └── telegram_bot.py             # Integración opcional con Telegram
│   ├── frontend/                       # Archivos de interfaz web (consola y gráficos)
│   ├── mcp/                            # Carpeta modularizada de servidores MCP
│   │   ├── __init__.py
│   │   ├── finance/                    # Finanzas / gastos (Port 8002)
│   │   │   ├── __init__.py
│   │   │   ├── tools.py                # Definición de herramientas financieras
│   │   │   └── server.py               # Servidor MCP de finanzas
│   │   └── reminder/                   # Recordatorios CRUD (Port 8003)
│   │       ├── __init__.py
│   │       ├── tools.py                # Definición de herramientas de recordatorios
│   │       └── server.py               # Servidor MCP de recordatorios
│   ├── services/
│   │   ├── llm.py                      # Lógica de integración con OpenAI
│   │   ├── rag.py                      # ChromaDB + embeddings locales
│   │   └── persistence/
│   │       ├── db.py
│   │       ├── expense_persistence.py
│   │       └── reminder_persistence.py
├── rag_docs/                           # Documentos para RAG (.txt y .pdf)
├── documentation/                      # Documentación técnica del proyecto (arquitectura, frontend)
└── README.md                           # Documento principal del repositorio
```

---

## Endpoints de la Capa de Presentación (Puerto 8000)

| Método | Ruta | Descripción | Consumidor |
|--------|------|-------------|------------|
| `GET` | `/` | Health check del backend | Monitoreo |
| `GET` | `/app` | Sirve la consola web frontend | Navegador |
| `POST` | `/message` | Punto de entrada del agente conversacional | Frontend, Telegram |
| `GET` | `/expenses` | Datos crudos y agregados de la BD relacional | Frontend |
| `GET` | `/reminders` | Lista de recordatorios del itinerario | Frontend |
| `GET` | `/status` | Estado dinámico agregado de subsistemas y MCPs | Frontend, Monitoreo |
| `GET` | `/mcp/tools` | Catálogo unificado de herramientas MCP | Frontend |

---

## Herramientas MCP Unificadas (9 totales)

| Herramienta | Servidor Origen | Puerto | Parámetros Requeridos |
|-------------|-----------------|--------|-----------------------|
| `budget` | `finance_server` | 8002 | Ninguno |
| `record_expense` | `finance_server` | 8002 | `amount` (float), `description` (str), `category` (str) |
| `query_expenses` | `finance_server` | 8002 | Ninguno (opcional `category` (str)) |
| `modify_expense` | `finance_server` | 8002 | `id` (int), opcionales `amount`, `description`, `category` |
| `delete_expense` | `finance_server` | 8002 | `id` (int) |
| `record_reminder` | `reminder_server` | 8003 | `title` (str), `due_time` (str), `note` (str) opcional |
| `query_reminders` | `reminder_server` | 8003 | Ninguno |
| `modify_reminder` | `reminder_server` | 8003 | `id` (int), opcionales `title`, `due_time`, `note` |
| `delete_reminder` | `reminder_server` | 8003 | `id` (int) |

Adicionalmente, el agente expone localmente las herramientas `rules` y `logistics`.

---

## Estado Técnico Global
- **Backend de Presentación**: ✅ **COMPLETADO & ONLINE**
- **Servidor de Finanzas (8002)**: ✅ **COMPLETADO & ONLINE**
- **Servidor de Recordatorios (8003)**: ✅ **COMPLETADO & ONLINE**
- **Integridad del Negocio**: La modularización de las carpetas respeta el Clean Architecture, desacoplando los servicios de las capas de transporte y serialización.

*Última actualización: Mayo 2026*