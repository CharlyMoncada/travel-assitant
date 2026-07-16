# Suite de Tests — Travel Assistant

Documento consolidado de la suite de tests unitarios e integración del proyecto.  
Fichero único de tests: `scratch/test_suite.py`.

---

## Resumen por rama

| Rama                 | Tests añadidos | Clases nuevas |
|----------------------|---------------|---------------|
| `main` (original)    | 12 clases     | —             |
| `tests_memory`       | +5 clases     | `TestDetectMemoryToSave`, `TestMemoryPersistence`, `TestConversationPersistence`, `TestChatMemoryServicePersistentHistory`, `TestBuildMemoryContext` |

---

## Clases de tests

### 1. `TestLanguageGuardrail`

**Módulo probado:** `app/agents/orchestrator/guardrails_input.py`

Verifica que el guardrail de idioma acepta inglés y español y rechaza cualquier otro.

| Test | Descripción |
|------|-------------|
| `test_english_accepted` | El inglés pasa el guardrail |
| `test_spanish_accepted` | El español pasa el guardrail |
| `test_french_rejected` | El francés es bloqueado |
| `test_german_rejected` | El alemán es bloqueado |
| `test_short_text_accepted` | Textos cortos (< umbral langdetect) se dejan pasar |

---

### 2. `TestTelegramResponseChunking`

**Módulo probado:** `app/interfaces/telegram_bot.py`

Comprueba que mensajes largos se dividen en fragmentos de ≤ 4096 caracteres para la API de Telegram.

| Test | Descripción |
|------|-------------|
| `test_short_message_no_split` | Un mensaje corto se envía de una sola vez |
| `test_long_message_split` | Un mensaje > 4096 chars se trocea correctamente |

---

### 3. `TestAgentFocusDirectives`

**Módulo probado:** `app/agents/*/prompts.py`

Verifica que los prompts de sistema de cada agente contienen las directivas de enfoque correctas y no exceden un límite razonable de tokens.

| Test | Descripción |
|------|-------------|
| `test_finance_prompt_contains_required_sections` | El prompt de finanzas incluye secciones clave |
| `test_reminder_prompt_contains_required_sections` | El prompt de recordatorios incluye secciones clave |
| `test_general_prompt_contains_required_sections` | El prompt del agente general incluye secciones clave |
| `test_prompts_are_not_excessively_long` | Ningún prompt supera 4000 palabras |

---

### 4. `TestInjectionGuardrail`

**Módulo probado:** `app/agents/orchestrator/guardrails_input.py`

Verifica el bloqueo de patrones de prompt injection.

| Test | Descripción |
|------|-------------|
| `test_ignore_previous_instructions` | Bloquea "ignore previous instructions" |
| `test_system_prompt_leak` | Bloquea intentos de extraer el system prompt |
| `test_roleplay_jailbreak` | Bloquea "pretend you are a…" |
| `test_normal_message_passes` | Un mensaje legítimo no se bloquea |
| `test_injection_in_spanish` | Variantes en español también bloqueadas |

---

### 5. `TestOutputIntegrityGuardrail`

**Módulo probado:** `app/agents/orchestrator/guardrails_output.py`

Verifica que la respuesta del agente no contiene trazas de sistema ni el system prompt.

| Test | Descripción |
|------|-------------|
| `test_traceback_blocked` | Respuesta con `Traceback` es rechazada |
| `test_system_prompt_leak_blocked` | Respuesta que empieza por "System:" es rechazada |
| `test_clean_response_passes` | Una respuesta normal pasa sin modificaciones |

---

### 6. `TestMemoryDetection`

**Módulo probado:** `app/agents/orchestrator/history_manager.py`

Tests de la detección de preferencias de viaje en mensajes de usuario (lógica pura, sin BD).

| Test | Descripción |
|------|-------------|
| `test_detects_airport_preference` | Detecta aeropuerto favorito |
| `test_no_preference_in_generic_message` | Un mensaje genérico no genera memoria |
| `test_question_not_stored_as_memory` | Las preguntas se ignoran |

---

### 7. `TestMemoryContextBuilder`

**Módulo probado:** `app/agents/orchestrator/history_manager.py`

Verifica que el contexto ensamblado para el agente incluye tanto la memoria a largo plazo como la conversación previa.

| Test | Descripción |
|------|-------------|
| `test_empty_memories_return_raw_message` | Sin memorias, se devuelve el mensaje en crudo |
| `test_long_term_memory_included` | La memoria a largo plazo aparece en el contexto |
| `test_short_term_memory_included` | El historial de conversación aparece en el contexto |

---

### 8. `TestExpensePersistence`

**Módulo probado:** `app/services/persistence/expense_persistence.py`

Tests CRUD de gastos usando mocks de la sesión de SQLAlchemy.

| Test | Descripción |
|------|-------------|
| `test_save_expense_returns_correct_fields` | `save_expense` devuelve los campos correctos |
| `test_delete_expense_not_found_returns_error` | Borrar un ID inexistente devuelve error |
| `test_modify_expense_not_found_returns_error` | Modificar un ID inexistente devuelve error |

---

### 9. `TestReminderPersistence`

**Módulo probado:** `app/services/persistence/reminder_persistence.py`

Tests CRUD de recordatorios usando mocks de la sesión SQLAlchemy.

| Test | Descripción |
|------|-------------|
| `test_save_reminder_returns_correct_fields` | `save_reminder` devuelve los campos correctos |
| `test_delete_reminder_not_found_returns_error` | Borrar un ID inexistente devuelve error |
| `test_modify_reminder_not_found_returns_error` | Modificar un ID inexistente devuelve error |

---

### 10. `TestSupervisorRouting`

**Módulo probado:** `app/agents/supervisor/agent.py`

Tests de las decisiones de enrutamiento del supervisor (requiere `OPENAI_API_KEY`).

| Test | Descripción |
|------|-------------|
| `test_finance_query_routed_to_finance` | "Añade un gasto" → ruta `finance` |
| `test_reminder_query_routed_to_reminder` | "Recuérdame comprar entradas" → ruta `reminder` |
| `test_general_query_routed_to_general` | "¿Qué tiempo hace en Roma?" → ruta `general` |

---

### 11. `TestMemoryPruningSimulation`

**Módulo probado:** `app/agents/orchestrator/history_manager.py`

Simula la poda de historial de conversación cuando supera el límite de tokens/mensajes.

| Test | Descripción |
|------|-------------|
| `test_pruning_keeps_recent_messages` | Solo se conservan los N mensajes más recientes |
| `test_pruning_preserves_message_order` | El orden cronológico se mantiene tras la poda |

---

### 12. `TestOrchestratorConcurrency`

**Módulo probado:** `app/agents/orchestrator/orchestrator.py`

Verifica que el orquestador ejecuta múltiples agentes en paralelo cuando el supervisor devuelve varias rutas.

| Test | Descripción |
|------|-------------|
| `test_concurrent_execution_performance` | 3 agentes mock de 0.5 s terminan en < 1 s total |

---

### 13. `TestDetectMemoryToSave` *(rama `tests_memory`)*

**Módulo probado:** `app/agents/orchestrator/history_manager.py` — método `detect_memory_to_save`

Lógica pura de detección de preferencias declarativas del usuario. Sin acceso a BD.

| Test | Descripción |
|------|-------------|
| `test_detects_favorite_airport_spanish` | "Mi aeropuerto favorito es…" → `favorite_airport` |
| `test_detects_favorite_airport_english` | "My favorite airport is…" → `favorite_airport` |
| `test_detects_budget_spanish` | "Mi presupuesto es…" → `budget_preference` |
| `test_detects_budget_english` | "My budget is…" → `budget_preference` |
| `test_detects_travel_style_spanish` | "Prefiero viajar…" → `travel_style` |
| `test_detects_travel_style_english_prefer_to` | "I prefer to travel…" → `travel_style` |
| `test_detects_travel_style_english_prefer_traveling` | "I prefer traveling…" → `travel_style` |
| `test_question_with_interrogation_not_saved` | Mensajes con `¿` no generan memoria |
| `test_question_with_what_not_saved` | Mensajes con `what` no generan memoria |
| `test_generic_message_returns_none` | Mensaje genérico devuelve `None` |

---

### 14. `TestMemoryPersistence` *(rama `tests_memory`)*

**Módulo probado:** `app/services/persistence/memory_persistence.py`

Tests de integración con una BD SQLite temporal en memoria. Verifica `save_user_memory`, `get_user_memories` y `format_user_memories`.

| Test | Descripción |
|------|-------------|
| `test_save_and_retrieve_single_memory` | Guardar y recuperar una preferencia |
| `test_save_multiple_keys_same_thread` | Múltiples claves en el mismo thread |
| `test_upsert_updates_existing_value` | Guardar la misma clave actualiza el valor (UPSERT) |
| `test_thread_isolation` | Dos threads no comparten memorias |
| `test_empty_thread_returns_empty_list` | Thread sin datos → lista vacía |
| `test_format_returns_non_empty_string` | `format_user_memories` devuelve texto legible |
| `test_format_empty_thread_returns_empty_string` | Thread vacío → cadena vacía |

---

### 15. `TestConversationPersistence` *(rama `tests_memory`)*

**Módulo probado:** `app/services/persistence/conversation_persistence.py`

Tests de integración con BD temporal para `save_message` y `get_recent_messages`.

| Test | Descripción |
|------|-------------|
| `test_save_and_retrieve_message` | Guardar y recuperar un mensaje |
| `test_roles_preserved` | Los roles `user`/`assistant` se conservan |
| `test_messages_returned_in_chronological_order` | Los mensajes vienen en orden cronológico |
| `test_limit_respected` | El parámetro `limit` reduce correctamente el resultado |
| `test_thread_isolation` | Dos threads no comparten mensajes |
| `test_empty_thread_returns_empty_list` | Thread sin mensajes → lista vacía |

---

### 16. `TestChatMemoryServicePersistentHistory` *(rama `tests_memory`)*

**Módulo probado:** `app/agents/orchestrator/history_manager.py` — métodos `get_persistent_history` y `format_persistent_memory`

Usa mocks de `get_recent_messages`.

| Test | Descripción |
|------|-------------|
| `test_get_persistent_history_returns_langchain_messages` | Devuelve `HumanMessage`/`AIMessage` correctos |
| `test_get_persistent_history_skips_empty_content` | Los mensajes con contenido vacío se omiten |
| `test_get_persistent_history_returns_empty_on_db_error` | Si la BD falla, devuelve `[]` sin crash |
| `test_format_persistent_memory_returns_string` | Devuelve un string con `user:` / `assistant:` |
| `test_format_persistent_memory_returns_empty_string_on_error` | Si la BD falla, devuelve `""` |

---

### 17. `TestBuildMemoryContext` *(rama `tests_memory`)*

**Módulo probado:** `app/agents/orchestrator/history_manager.py` — método `build_memory_context_for_agent`

Lógica pura de ensamblado del contexto para el agente. Sin BD.

| Test | Descripción |
|------|-------------|
| `test_no_memory_returns_raw_message` | Sin memorias, el mensaje se devuelve tal cual |
| `test_long_term_memory_prepended` | La memoria a largo plazo se antepone al mensaje |
| `test_short_term_memory_prepended` | El historial de conversación se antepone al mensaje |
| `test_both_memories_in_output` | Ambas memorias aparecen en el contexto |
| `test_current_message_always_last` | El mensaje actual siempre es el último |

---

## Cómo ejecutar

```bash
# Todos los tests
python -m unittest scratch.test_suite -v

# Sólo los tests de memoria (rama tests_memory)
python -m unittest \
  scratch.test_suite.TestDetectMemoryToSave \
  scratch.test_suite.TestMemoryPersistence \
  scratch.test_suite.TestConversationPersistence \
  scratch.test_suite.TestChatMemoryServicePersistentHistory \
  scratch.test_suite.TestBuildMemoryContext \
  -v
```

---

## Tests manuales — Memoria y Preferencias de Usuario

### 1. Guardar preferencia de aeropuerto

```bash
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Mi aeropuerto favorito es el Adolfo Suárez Madrid-Barajas", "thread_id": "smoke-test-1"}' \
  | python3 -m json.tool
```

**Esperado:** respuesta afirmativa del asistente confirmando que ha registrado la preferencia.

### 2. Guardar presupuesto de viaje

```bash
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Mi presupuesto es 800 euros por viaje", "thread_id": "smoke-test-1"}' \
  | python3 -m json.tool
```

### 3. Guardar estilo de viaje

```bash
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Prefiero viajar en temporada baja para evitar aglomeraciones", "thread_id": "smoke-test-1"}' \
  | python3 -m json.tool
```

### 4. Verificar que la memoria persiste entre mensajes

```bash
# Enviar un mensaje nuevo y comprobar que el asistente recuerda las preferencias anteriores
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "¿Cuál es mi aeropuerto favorito?", "thread_id": "smoke-test-1"}' \
  | python3 -m json.tool
```

**Esperado:** el asistente menciona "Adolfo Suárez" o "Barajas" sin que el usuario lo haya repetido.

### 5. Aislamiento de threads

```bash
# Thread diferente no debe conocer las preferencias del thread anterior
curl -s -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"text": "¿Cuál es mi aeropuerto favorito?", "thread_id": "smoke-test-OTRO"}' \
  | python3 -m json.tool
```

**Esperado:** el asistente indica que no tiene información de ese usuario o pide que la proporcione.

### 6. Verificar en BD (sqlite3)

```bash
sqlite3 data/travel_assistant.db "SELECT thread_id, memory_key, memory_value FROM user_memories;"
sqlite3 data/travel_assistant.db "SELECT thread_id, role, substr(content,1,60) FROM conversation_messages ORDER BY id DESC LIMIT 10;"
```

---

## Corrección de bug aplicada en esta rama

`memory_persistence.py` y `conversation_persistence.py` usaban `DB_PATH = Path("travel_assistant.db")` (ruta raíz). Se ha corregido a `Path("data/travel_assistant.db")` para que sean consistentes con el cambio introducido en la rama `fix_data` (que actualiza `db.py` y `docker-compose.yml`).
