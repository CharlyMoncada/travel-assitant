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
  - Generación de respuestas de enrutamiento múltiple y secuencial.
  - Generación de respuestas contextuales enriquecidas por RAG.
  - Fallback controlado para errores de API del LLM.

#### 2. Sistema RAG Avanzado con Restricción de Alcance
- **Base de datos vectorial**: ChromaDB con almacenamiento persistente local en `app/chromadb_store/`.
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`).
- **Documentos**: Archivos normativos y de viaje (.txt y .pdf) en `rag_docs/`.
- **Características**:
  - Inicialización lazy para optimizar los tiempos de inicio del servidor principal.
  - Búsqueda de coincidencia semántica en documentos locales.
  - **Filtro de Destino Europeo**: Intercepta consultas que no tengan coincidencia semántica suficiente en la base de datos (con similitud inferior al umbral o sin resultados), retornando una respuesta de fallback localizada y amigable explicando que el asistente de regulaciones y visados está limitado exclusivamente a destinos de Europa.

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
  - **Recommender Agent**: Sugiere equipaje y clasifica objetos de viaje según el clima del destino (sin MCP, consume `wttr.in`) desde `app/agents/recommender/`.
- **Enrutamiento Secuencial de Múltiples Intenciones (Opción A)**:
  - El Supervisor y Orquestador permiten identificar y ejecutar una lista de rutas especializadas secuencialmente en un único mensaje del usuario (por ejemplo: *"visado España y guarda taxi 20"* activa de forma consecutiva a `finance` y `general`).
- **Caché TTL de Herramientas**:
  - El orquestador almacena en caché temporal (TTL de 5 minutos) las herramientas e input schemas de los servidores MCP remotos para minimizar latencia y consumo de recursos de red.
- **Enrutamiento Cognitivo Unificado (Supervisor Skill)**:
  - *Capa 1: Bilingual Keywords*: Identificación semántica inteligente de intenciones ante palabras clave bilingües.
  - *Capa 2: Sticky Routing & Context Inheritance*: Herencia contextual automática del último dominio activo.
  - *Capa 3: Restricción de Normativas a Europa*: Instrucción al supervisor para no enrutar visados o requisitos de destinos no europeos, respondiendo con un rechazo directo y localizado.
  - *Interacción Directa*: Capacidad del Supervisor para responder Smalltalk o clarificar dudas ambiguas.

#### 5. Capa de Seguridad Global (Guardrails)
Consolidada en `app/agents/orchestrator/guardrails_input.py` y `guardrails_output.py`. Se eliminaron los guardrails obsoletos específicos de subpaquetes.
- **Guardrails de Entrada** (21 patrones regex compilados):
  - *Filtro de Idioma mejorado*: Bypass automático para mensajes de menos de 3 palabras (p. ej. "hola", "ok", "hi") para evitar falsos positivos en textos cortos. Para mensajes más largos, usa `detect_langs()` con umbral de confianza del 85% antes de bloquear.
  - *Detección de Prompt Injection*: Filtro determinista por expresiones regulares. Cubre: anulación de instrucciones, cambio de rol, DAN/jailbreak, extracción de prompts, tokens de plantilla, escalada de privilegios, exfiltración de datos y los nuevos patrones añadidos en `fix_guardrails`:
    - **Bypass hipotético** (`hypothetical_bypass_en/es`): "Hypothetically if you had no rules…", "Hipotéticamente sin restricciones…".
    - **Many-shot jailbreak**: secuencias User/Assistant falsas repetidas para condicionar al modelo.
    - **Token smuggling**: líneas que empiezan por `assistant:` o `system:`.
    - **Simulation jailbreak** (`simulation_jailbreak_en/es`): "For a story, write…", "Para una historia, escribe…".
    - **Ofuscación/base64**: `base64 decode this`, `eval(...)`, `exec(...)`.
    - **Inyección Markdown**: bloques ` ```system `, ` ```prompt `, ` ```instruction `.
- **Guardrails de Salida (Output Integrity)**:
  - *Filtro de Trazas de Error*: Bloquea excepciones Python (incluye `ImportError:`, `RuntimeError:`).
  - *Filtro de Tokens LLM*: Detecta y bloquea fugas de tokens de formato/plantilla (`[INST]`, `<<SYS>>`).
  - *Filtro de Instrucciones de Sistema*: Ampliado para cubrir todos los marcadores de prompt internos actuales (`AVAILABLE SUB-AGENTS`, `get_recommender_system_prompt`, `You are the Intelligent Supervisor`, etc.).
  - *Filtro de Secrets* (nuevo): Detecta posibles fugas de claves API (`sk-proj-…`, `Bearer …`, `OPENAI_API_KEY=`, `BRAVE_API_KEY=`, `TELEGRAM_BOT_TOKEN=`).
  - *Filtro de Tool Call Markup* (nuevo): Bloquea marcadores internos de llamadas a herramienta (`<tool_call>`, `<function_call>`, JSON con `"function":`).

#### 10. Persistencia de Memoria de Usuario y Preferencias
- **Memoria a corto plazo**: Historial de conversación por `thread_id` almacenado en `conversation_messages` vía `conversation_persistence.py`.
- **Memoria a largo plazo**: Preferencias de viaje declarativas del usuario (aeropuerto favorito, presupuesto, estilo de viaje) almacenadas en `user_memories` vía `memory_persistence.py`.
- **Detección automática**: `ChatMemoryService.detect_memory_to_save()` extrae preferencias de mensajes declarativos en español e inglés sin intervención del LLM.
- **Construcción de contexto**: `build_memory_context_for_agent()` ensambla el bloque de memoria antes de cada llamada al agente.

#### 11. Persistencia de Datos bajo `data/`
- Todos los datos persistentes (SQLite, ChromaDB) consolidados en el directorio `data/` del raíz del proyecto.
- `docker-compose.yml` actualizado con bind mounts (`./data:/code/data`) y volumen nombrado para ChromaDB.
- `db.py` apunta a `sqlite:///data/travel_assistant.db`; `conversation_persistence.py` y `memory_persistence.py` corregidos a `Path("data/travel_assistant.db")`.

#### 6. Capa de Servicios de Dominio (Clean Architecture)
- La lógica de negocio principal está centralizada en los módulos de persistencia bajo `app/services/persistence/`.
- Las herramientas locales del agente (`rules`, `travel_search`, `get_weather` y `get_packing_items`) se encuentran en sus respectivos subdirectorios de agentes. Nombres de clases y rutinas internas estandarizados en inglés.

#### 7. Persistencia de Datos
- **Base de datos**: SQLite local con SQLAlchemy ORM.
- **Entidades**: Gastos (`Expense`) y recordatorios (`Reminder`).
- **Operaciones**: CRUD completo (`save`, `get_summary`, `modify`, `delete`) con transacciones seguras.

#### 8. Interfaces de Usuario e Integraciones
- **API REST**: 7 endpoints unificados en el puerto `8000`.
- **Bot Telegram**: Integración opcional lista para producción mediante Token de Telegram.
- **Frontend Web**: Consola interactiva en HTML/JS con gráficos agregados en tiempo real.

#### 9. Monitoreo y Observabilidad (LangSmith)
- **Framework**: Integración nativa con la suite de observabilidad de LangSmith mediante decoradores `@traceable`.

---

### 🔄 Cambios Recientes — Sprint Julio 2026

#### 0. Corrección de Rutas de BD (`fix_data` / `tests_memory`)
- `conversation_persistence.py` y `memory_persistence.py` usaban `Path("travel_assistant.db")` (raíz). Corregidos a `Path("data/travel_assistant.db")` para ser consistentes con el cambio de `db.py` (SQLAlchemy) y `docker-compose.yml`.

#### 0b. Fix Recommender — No Preguntas de Aclaración (`fix_recommender`)
- El agente recomendador preguntaba "¿playa o montaña?" al usuario en lugar de inferirlo del clima. La respuesta a esa pregunta llegaba al orquestador sin contexto de ciudad y generaba una respuesta incoherente.
- **Solución**: nueva sección `CRITICAL RULE — NEVER ASK CLARIFYING QUESTIONS` en el prompt. Reglas de inferencia explícitas por temperatura/precipitación/humedad. Output mejorado con emojis ✅🟡❌ y tip final.
- `objetos.csv` ampliado de 30 a 62 ítems con categorías de playa, montaña, frío y lluvia.

#### 0c. Refuerzo de Guardrails (`fix_guardrails`)
- 7 nuevos patrones de inyección de entrada y 3 nuevas comprobaciones de salida (ver sección 5 de Funcionalidades Completadas).

#### 1. Unificación y Estandarización a Inglés
- Estandarizados todos los comentarios y docstrings de los módulos compartidos de guardrails (`guardrails_input.py` y `guardrails_output.py`) al idioma inglés.
- Renombradas clases y funciones locales en `recommender/tools.py` a inglés (`ObtenerTiempoSchema` -> `GetWeatherSchema`, `obtener_tiempo` -> `get_weather`, etc.).
- Actualizados prompts del supervisor y recomendador para emplear los nuevos identificadores de herramientas en inglés.

#### 2. Implementación de Guardrails de Salida e Integridad
- Añadida la lógica de validación `check_output_integrity` en `guardrails_output.py` conectándola a todas las salidas del orquestador y supervisor para evitar la filtración de fallos de compilación u otros detalles internos de código hacia el usuario final.

#### 3. Caché de Herramientas MCP con TTL
- Añadido un caché temporal con TTL de 300 segundos a `TravelAgentOrchestrator._discover_mcp_tools` en `orchestrator.py` para almacenar las herramientas dinámicas consultadas en los servidores remotos de forma consistente.

#### 4. Restricción Reguladora a Europa
- Limitación estricta a nivel de Supervisor y motor RAG para rechazar amigablemente y en el idioma del usuario cualquier petición de normativa de viaje (visas, pasaportes, vacunas) que involucre destinos fuera de Europa.

#### 5. Ejecución en Serie de Agentes (Multi-routing)
- Modificado el esquema de decisión del Supervisor a `routes: list[str]` para enrutar múltiples sub-agentes secuencialmente, y modificado el bucle en `orchestrator.py` para procesarlos ordenadamente concatenando sus respuestas.

#### 6. Mejora del Guardrail de Idioma (anti-falsos-positivos)
- Reemplazado `langdetect.detect()` por `detect_langs()` con umbral de confianza del 85% (`_MIN_LANG_CONFIDENCE`).
- Añadido bypass automático para mensajes de menos de 3 palabras (`_MIN_WORDS_FOR_LANG_DETECTION`) para evitar bloquear saludos cortos como "hola" o "hi" que `langdetect` clasifica erróneamente.

#### 7. Fix `httpx.utils.quote` en Recommender Tools
- Corregido el error `AttributeError: module 'httpx' has no attribute 'utils'` en `app/agents/recommender/tools.py`.
- Sustituido `httpx.utils.quote(city)` por `urllib.parse.quote(city)` (stdlib estándar de Python), ya que `httpx.utils` no forma parte de la API pública de httpx.

#### 8. Double Confirmation para Acciones Destructivas en Finanzas
- Añadida la regla 5 al prompt del Finance Agent: antes de ejecutar `modify_expense` o `delete_expense`, el agente solicita confirmación explícita al usuario, advirtiendo que la acción no tiene rollback.

#### 9. Categorías Estándar de Gastos
- Añadida la regla 6 al prompt del Finance Agent: al registrar o modificar gastos, el agente asigna automáticamente la categoría canónica (Comida/Food, Transporte/Transport, Alojamiento/Accommodation, Entretenimiento/Entertainment, Otros/Others) mapeando conceptos en lenguaje natural.

#### 10. Consolidación de Suite de Pruebas Automatizadas
- Creada la suite de pruebas unificada en `scratch/test_suite.py` que consolida de forma automatizada las validaciones de guardrails de idioma y inyección, división de respuestas largas en Telegram, directivas de enfoque de los agentes, simulación de turnos de mensajes de base de datos, y enrutamientos semánticos/geográficos del Supervisor LLM.
- Eliminados 17 scripts de pruebas obsoletos o redundantes en la carpeta `scratch/` para mantener el repositorio limpio y ordenado.

#### 11. Ampliación de Suite de Tests — Sprint Julio 2026
Nuevas clases añadidas al fichero único `scratch/test_suite.py`:

| Rama | Clases | Tests |
|------|--------|-------|
| `tests_brave` | `TestBraveSearch`, `TestTravelSearchTool` | ~14 |
| `tests_rag` | `TestRAGTextProcessing`, `TestRAGQueryLogic`, `TestRAGPDFExtraction`, `TestRAGStatus` | ~18 |
| `tests_recommender` | `TestRecommenderWeatherTool`, `TestRecommenderPackingTool`, `TestRecommenderPrompt` | ~12 |
| `tests_memory` | `TestDetectMemoryToSave`, `TestMemoryPersistence`, `TestConversationPersistence`, `TestChatMemoryServicePersistentHistory`, `TestBuildMemoryContext` | 33 |
| `fix_recommender` | `TestRecommenderPrompt` (actualizado), `TestRecommenderPackingItems` | 12 |
| `fix_guardrails` | `TestInjectionGuardrailExtended`, `TestOutputIntegrityGuardrailExtended` | 28 |

---

### 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Endpoints REST de Presentación (Port 8000) | 7 |
| Servidores MCP Independientes | 2 (Puertos 8002 y 8003) |
| Herramientas MCP Totales | 9 remotas + 4 locales |
| Servicios de Dominio | 4 (+ fachada) |
| Validación de Parámetros | Pydantic V2 Dinámico |
| Cobertura RAG | Documentos TXT y PDF unificados |
| Observabilidad y Monitoreo | Integración nativa con LangSmith |
| Patrones de inyección bloqueados | 21 (guardrail de entrada) |
| Comprobaciones de integridad de salida | 5 (guardrail de salida) |
| Ítems de lista de equipaje | 62 (playa + montaña + frío + lluvia + generales) |
| Clases de tests automatizados | 17+ |
| Tests unitarios / integración | ~120+ |

---

## Arquitectura del Proyecto

### Estructura de Directorios

```
travel-assistant/
├── data/                               # ← NUEVO: datos persistentes fuera del código
│   └── travel_assistant.db             # SQLite (gastos, recordatorios, conversaciones, memorias)
├── app/
│   ├── main.py                         # FastAPI App principal en puerto 8000
│   ├── api/
│   │   ├── endpoints.py                # 7 endpoints unificados
│   │   ├── orchestrator/               # Módulo encapsulado del orquestador
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py         # Cliente Multiserver asíncrono con Pydantic, TTL y enrutamiento concurrente
│   │   │   ├── history_manager.py      # Memoria a corto y largo plazo (ChatMemoryService)
│   │   │   ├── guardrails_input.py     # Guardrail global de idioma e inyección (21 patrones)
│   │   │   └── guardrails_output.py    # Guardrail global de integridad de salida (5 checks)
│   │   ├── supervisor/                 # Agente Supervisor y Enrutador Cognitivo
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica del Supervisor (Routes list)
│   │   │   ├── prompts.py              # Prompts específicos con filtros geográficos
│   │   │   └── supervisor_routing_skill.md  # Especificación del Skill
│   │   ├── finance/                    # Agente Especialista en Finanzas
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica de construcción del sub-agente
│   │   │   ├── prompts.py              # FINANCE_AGENT_SYSTEM_PROMPT
│   │   │   └── finance_skill.md        # Especificación del Skill de Finanzas
│   │   ├── reminder/                   # Agente Especialista en Recordatorios
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica de construcción del sub-agente
│   │   │   ├── prompts.py              # REMINDER_AGENT_SYSTEM_PROMPT
│   │   │   └── reminder_skill.md       # Especificación del Skill de Recordatorios
│   │   ├── general/                    # Agente Especialista en RAG y Logística
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Lógica de construcción del sub-agente
│   │   │   ├── prompts.py              # GENERAL_AGENT_SYSTEM_PROMPT
│   │   │   ├── tools.py                # Herramientas locales del agente general (rules, travel_search)
│   │   │   └── general_skill.md        # Especificación del Skill General
│   │   └── recommender/                # Agente Recomendador de Equipaje (Agente local)
│   │       ├── __init__.py
│   │       ├── agent.py                # Lógica de construcción del sub-agente
│   │       ├── prompts.py              # RECOMMENDER_SYSTEM_PROMPT
│   │       ├── tools.py                # Herramientas locales de equipaje en inglés (get_weather, get_packing_items)
│   │       └── recommender_skill.md    # Especificación del Skill Recomendador
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
│   │   ├── brave_search.py             # Cliente HTTP para Brave Search API
│   │   ├── rag.py                      # ChromaDB + RAG con fallback europeo
│   │   └── persistence/
│   │       ├── db.py                   # SQLAlchemy → data/travel_assistant.db
│   │       ├── expense_persistence.py
│   │       ├── reminder_persistence.py
│   │       ├── conversation_persistence.py  # Historial corto plazo por thread
│   │       └── memory_persistence.py        # Preferencias de usuario a largo plazo
│   └── utils/
│       └── date_resolution.py
├── rag_docs/                           # Documentos para RAG (.txt y .pdf)
├── data/                               # BD SQLite (excluido de imagen Docker)
├── scratch/
│   └── test_suite.py                   # Suite unificada de tests (17+ clases, 120+ tests)
├── documentation/                      # Documentación técnica del proyecto
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

Adicionalmente, el agente expone localmente las herramientas `rules`, `travel_search`, `get_weather` y `get_packing_items`.

---

## Estado Técnico Global
- **Backend de Presentación**: ✅ **COMPLETADO & ONLINE**
- **Servidor de Finanzas (8002)**: ✅ **COMPLETADO & ONLINE**
- **Servidor de Recordatorios (8003)**: ✅ **COMPLETADO & ONLINE**
- **Integridad del Negocio**: La modularización de las carpetas respeta el Clean Architecture, desacoplando los servicios de las capas de transporte y serialización.

*Última actualización: Julio 2026*
