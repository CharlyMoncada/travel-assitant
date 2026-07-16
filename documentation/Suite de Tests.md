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

# Suite de Tests — Travel Assistant

## Descripción general

El proyecto cuenta con una suite de tests consolidada en `scratch/test_suite.py`. Todos los tests son unitarios o de integración ligera (sin levantar servidores), usando `unittest` estándar de Python y `unittest.mock` para aislar dependencias externas (LLM, HTTP, base de datos).

Los tests que requieren acceso real a la API de OpenAI están marcados con `IsolatedAsyncioTestCase` e incluyen un `skipTest` automático si `OPENAI_API_KEY` no está configurada.

---

## Ejecutar la suite

```bash
source .venv/bin/activate

# Suite completa
python -m unittest discover -s scratch -p "test_suite.py" -v

# Una clase concreta
python -m unittest scratch.test_suite.TestBraveSearch -v
python -m unittest scratch.test_suite.TestRAGTextProcessing -v
python -m unittest scratch.test_suite.TestRecommenderWeatherTool -v
```

---

## Clases de test

### 1. `TestLanguageGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_input.check_language`

| Test | Qué verifica |
|------|--------------|
| `test_allowed_languages` | Español e inglés pasan |
| `test_blocked_languages` | Portugués, italiano y francés bloqueados |
| `test_short_words_bypass` | < 3 palabras → siempre permitido |
| `test_romance_language_heuristics_overrides` | Palabras indicadoras del español evitan falsos positivos |
| `test_extra_cases` | Casos mixtos, puntuación especial, gibberish |

---

### 2. `TestTelegramResponseChunking`
**Módulo:** `app.connectors.telegram_bot.TelegramBotService._send_message_in_chunks`

| Test | Qué verifica |
|------|--------------|
| `test_short_message_single_chunk` | Mensajes cortos: 1 sola llamada |
| `test_long_message_newline_split` | Corte preferente en `\n` |
| `test_long_message_space_split` | Corte preferente en espacio |
| `test_long_message_hard_split` | Hard-cut a 4000 chars |
| `test_exactly_max_length` | Exactamente 4000 chars: 1 llamada |
| `test_empty_message` | Mensaje vacío: 1 llamada con `""` |

---

### 3. `TestAgentFocusDirectives`
**Módulo:** `app.agents.orchestrator.agent_executor.SubAgentExecutor.get_agent_focus_directive`

| Test | Qué verifica |
|------|--------------|
| `test_finance_focus_directive` | Contiene "Finance" y "finance-related" |
| `test_reminder_focus_directive` | Contiene "Reminders" y "reminder-related" |
| `test_recommender_focus_directive` | Contiene "Recommender" y "weather" |
| `test_general_focus_directive` | Contiene "General" y "searches" |
| `test_invalid_route_focus_directive` | Ruta desconocida → `""` |
| `test_nonnegotiable_label` | Todos usan etiqueta `NON-NEGOTIABLE` |
| `test_multi_intent_isolation_language` | Todos incluyen `silently ignore` |

---

### 4. `TestInjectionGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_input.check_prompt_injection`

| Test | Qué verifica |
|------|--------------|
| `test_instruction_override_en/es` | "ignore all previous instructions" EN/ES |
| `test_forget_instructions_en/es` | "forget your instructions" EN/ES |
| `test_new_instructions_en/es` | "New instructions:" EN/ES |
| `test_role_hijack_en/es` | "you are now / act as" EN/ES |
| `test_dan_jailbreak` | DAN, jailbreak, unrestricted mode |
| `test_prompt_extraction_en/es` | "Print your system prompt" EN/ES |
| `test_what_are_instructions_en/es` | "What are your instructions?" EN/ES |
| `test_privilege_escalation_en/es` | "developer mode / como administrador" EN/ES |
| `test_template_tokens` | `[INST]`, `<<SYS>>` y variantes |
| `test_data_exfiltration` | "leak/exfiltrate the database" |
| `test_safe_messages_not_blocked` | Mensajes legítimos no bloqueados |
| `test_returns_matched_pattern_name_on_block` | Devuelve nombre del patrón coincidente |

---

### 5. `TestOutputIntegrityGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_output.check_output_integrity`

| Test | Qué verifica |
|------|--------------|
| `test_template_token_leak` | `[INST]`, `<<SYS>>`, `### system` bloqueados |
| `test_raw_python_traceback_leak` | Tracebacks y excepciones Python bloqueados |
| `test_instruction_leak` | Frases de instrucciones del sistema bloqueadas |
| `test_failure_reason_returned` | Razón correcta (`raw_error_leak`, etc.) |
| `test_normal_responses_pass` | Respuestas normales pasan |

---

### 6. `TestMemoryDetection`
**Módulo:** `app.agents.orchestrator.history_manager.ChatMemoryService.detect_memory_to_save`

| Test | Qué verifica |
|------|--------------|
| `test_detects_favorite_airport_spanish/english` | Aeropuerto favorito en ES e EN |
| `test_detects_budget_spanish/english` | Preferencia de presupuesto |
| `test_detects_travel_style_spanish/english` | Estilo de viaje (tren, avión…) |
| `test_questions_not_saved` | Las preguntas nunca se guardan |
| `test_unrelated_messages_return_none` | Sin info de preferencia → `None` |

---

### 7. `TestMemoryContextBuilder`
**Módulo:** `app.agents.orchestrator.history_manager.ChatMemoryService.build_memory_context_for_agent`

| Test | Qué verifica |
|------|--------------|
| `test_returns_raw_message_when_no_context` | Sin memoria → mensaje original |
| `test_includes_long_term_memory` | Memoria a largo plazo en contexto |
| `test_includes_short_term_memory` | Historial reciente en contexto |
| `test_includes_both_memory_types` | Ambos tipos juntos |
| `test_message_always_at_end` | Mensaje actual siempre al final |

---

### 8. `TestExpensePersistence`
**Módulo:** `app.services.persistence.expense_persistence`

| Test | Qué verifica |
|------|--------------|
| `test_save_expense_returns_correct_fields` | Dict con id, amount, category, created_at |
| `test_delete_expense_not_found_returns_error` | ID inexistente → `"error"` |
| `test_modify_expense_not_found_returns_error` | Modificar ID inexistente → `"error"` |

---

### 9. `TestReminderPersistence`
**Módulo:** `app.services.persistence.reminder_persistence`

| Test | Qué verifica |
|------|--------------|
| `test_save_reminder_returns_correct_fields` | Dict con id, title, due_time, created_at |
| `test_delete_reminder_not_found_returns_error` | ID inexistente → `"error"` |
| `test_modify_reminder_not_found_returns_error` | Modificar ID inexistente → `"error"` |

---

### 10. `TestSupervisorRouting` _(requiere OPENAI_API_KEY)_
**Módulo:** `app.agents.supervisor.agent.run_supervisor`

| Test | Qué verifica |
|------|--------------|
| `test_pure_search_routing` | "buscar vuelo" → ruta `general` |
| `test_pure_finance_routing` | "registra un gasto" → ruta `finance` |
| `test_pure_reminder_routing` | "crear recordatorio" → ruta `reminder` |
| `test_pure_recommender_routing` | "qué empacar en la maleta" → ruta `recommender` |
| `test_chit_chat_direct_interaction` | "hola" → sin ruta, respuesta directa |
| `test_out_of_scope_rejection` | "quicksort en Python" → rechazo |
| `test_non_european_regulations_rejection` | Visado Japón → rechazo Europa |
| `test_multi_intent_routing` | Gasto + búsqueda → `finance` y `general` |

---

### 11. `TestMemoryPruningSimulation`

| Test | Qué verifica |
|------|--------------|
| `test_prune_history_turn_simulation` | Poda por límite de mensajes en DB |

---

### 12. `TestOrchestratorConcurrency`
**Módulo:** `app.agents.orchestrator.orchestrator.TravelAgentOrchestrator.handle_message`

| Test | Qué verifica |
|------|--------------|
| `test_concurrent_execution_performance` | 3 agentes × 0.5 s terminan en < 1 s (paralelismo real) |

---

### 13. `TestBraveSearch` _(rama: `tests_brave`)_
**Módulo:** `app.services.brave_search` — httpx mockeado

| Test | Qué verifica |
|------|--------------|
| `test_is_brave_available_false_when_no_key` | Sin API key → `False` |
| `test_is_brave_available_true_when_key_present` | Con API key → `True` |
| `test_no_api_key_returns_error_dict` | Sin key → `{error, results:[], query}` |
| `test_successful_search_returns_structured_result` | HTTP 200 → `{query, results[{title,url,desc}], total}` |
| `test_successful_search_empty_web_results` | HTTP 200 sin resultados → lista vacía, sin crash |
| `test_timeout_returns_error_dict` | `TimeoutException` → `"timed out"` en error |
| `test_http_401_returns_error_dict` | HTTP 401 → error con "401" |
| `test_http_429_returns_error_dict` | HTTP 429 → error con "429" |
| `test_format_search_results_for_llm_returns_valid_json` | JSON parseable con campos correctos |
| `test_format_search_results_for_llm_with_error_dict` | Dict de error también serializable |
| `test_format_search_results_preserves_non_ascii` | "España" se preserva (`ensure_ascii=False`) |

**Resultado:** `Ran 11 tests — OK`

---

### 14. `TestTravelSearchTool` _(rama: `tests_brave`)_
**Módulo:** `app.agents.general.tools.make_travel_search_coroutine`

| Test | Qué verifica |
|------|--------------|
| `test_short_query_appends_travel_keyword` | 2 palabras → añade `" travel"` |
| `test_query_of_three_words_appends_travel` | 3 palabras → también añade |
| `test_long_query_not_modified` | 5+ palabras → sin modificar |
| `test_no_api_key_returns_warning_json` | Sin Brave → JSON con `"warning"`, sin crash |
| `test_brave_exception_returns_error_json` | Excepción inesperada → JSON con `"error"` |

**Resultado:** `Ran 5 tests — OK`

---

### 15. `TestRAGTextProcessing` _(rama: `tests_rag`)_
**Módulo:** funciones puras `app.services.rag` — sin ChromaDB, embeddings ni LLM

| Test | Qué verifica |
|------|--------------|
| `test_normalize_strips_leading_trailing_whitespace` | Elimina espacios extremos |
| `test_normalize_replaces_cr_with_newline` | `\r\n` → `\n` |
| `test_normalize_removes_soft_hyphen_at_line_end` | `-\n` → palabras se unen |
| `test_normalize_collapses_multiple_spaces` | Múltiples espacios → uno |
| `test_normalize_collapses_excess_blank_lines` | > 2 líneas vacías → 2 |
| `test_normalize_empty_string_returns_empty` | `""` → `""` |
| `test_normalize_null_bytes_replaced` | `\x00` → espacio |
| `test_remove_noise_strips_urls` | URLs `https://` eliminadas |
| `test_remove_noise_strips_date_patterns` | Fechas tipo `1/6/2024, 10:30 AM` |
| `test_remove_noise_strips_your_europe_phrase` | "Your Europe" eliminado |
| `test_remove_noise_strips_menu_keyword` | "MENÚ" eliminado |
| `test_remove_noise_preserves_meaningful_content` | Contenido real conservado |
| `test_chunk_empty_string_returns_empty_list` | `""` → `[]` |
| `test_chunk_short_text_returns_single_chunk` | Texto corto → 1 chunk |
| `test_chunk_long_text_creates_multiple_chunks` | > 900 chars → varios chunks |
| `test_chunk_no_duplicates` | Chunks únicos |
| `test_chunk_all_content_covered` | Todos no vacíos |
| `test_chunk_paragraph_boundaries_respected` | Párrafos cortos separados quedan aparte |
| `test_content_hash_returns_hex_string` | SHA-1 = 40 hex chars |
| `test_content_hash_same_input_same_output` | Determinismo |
| `test_content_hash_different_inputs_differ` | Distintos inputs → distintos hashes |
| `test_last_words_returns_last_n` | Últimas N palabras |
| `test_last_words_shorter_than_n` | Texto < N → devuelve todo |
| `test_last_words_empty_string` | `""` → `""` |

**Resultado:** `Ran 24 tests — OK`

---

### 16. `TestRAGQueryLogic` _(rama: `tests_rag`)_
**Módulo:** `app.services.rag.query_normative_documents` — ChromaDB y LLM mockeados

| Test | Qué verifica |
|------|--------------|
| `test_empty_query_returns_specific_message` | `""` → "La consulta está vacía." |
| `test_whitespace_only_query_returns_specific_message` | Solo espacios → mismo mensaje |
| `test_no_close_results_returns_european_fallback_spanish` | Distancias > umbral + ES → fallback europeo en español |
| `test_no_close_results_returns_european_fallback_english` | Distancias > umbral + EN → fallback europeo en inglés |
| `test_good_results_calls_compose_rag_answer` | Distancias OK → `compose_rag_answer` llamado |
| `test_good_results_sources_contain_score` | `score = 1 - distance` en cada fuente |
| `test_results_filtered_by_max_distance` | Chunks lejanos excluidos de `sources` |

> **Nota de implementación:** `detect` y `compose_rag_answer` se importan localmente dentro de la función → hay que patchear en `langdetect.detect` y `app.services.llm.compose_rag_answer`, no en `app.services.rag`.

**Resultado:** `Ran 7 tests — OK`

---

### 17. `TestRAGPDFExtraction` _(rama: `tests_rag`)_
**Módulo:** `_build_chunks_from_pdf_file` / `_build_chunks_from_text_file` — ficheros reales de `rag_docs/`

| Test | Qué verifica |
|------|--------------|
| `test_txt_visa_produces_chunks` | `visa.txt` → ≥ 1 chunk |
| `test_txt_seguridad_chunk_has_expected_metadata` | type="text", source correcto |
| `test_txt_chunks_have_unique_ids` | IDs únicos |
| `test_pdf_ciudadanos_ue_produces_chunks` | PDF ciudadanos UE → ≥ 1 chunk |
| `test_pdf_chunks_are_non_empty_strings` | Todos los chunks son strings no vacíos |
| `test_pdf_chunks_have_page_metadata` | `page > 0` en metadata |
| `test_pdf_chunks_have_unique_ids` | IDs únicos |
| `test_pdf_pasaportes_produces_chunks` | PDF pasaportes → chunks |
| `test_pdf_menores_produces_chunks` | PDF menores → chunks |
| `test_pdf_content_contains_travel_keywords` | Contiene "pasaporte", "documento", "europa"… |
| `test_pdf_chunk_size_within_bounds` | Ningún chunk > `CHUNK_SIZE × 1.1` chars |

**Resultado:** `Ran 11 tests — OK`

---

### 18. `TestRAGStatus` _(rama: `tests_rag`)_
**Módulo:** `app.services.rag.rag_status`

| Test | Qué verifica |
|------|--------------|
| `test_rag_status_returns_all_expected_keys` | 8 campos exactos |
| `test_rag_status_document_count_matches_collection` | `document_count` = `collection.count()` |
| `test_rag_status_collection_count_error_returns_none` | `count()` lanza → `None` sin crash |
| `test_rag_status_collection_name_correct` | Coincide con constante `COLLECTION_NAME` |

**Resultado:** `Ran 4 tests — OK`

---

### 19. `TestRecommenderWeatherTool` _(rama: `tests_recommender`)_
**Módulo:** `app.agents.recommender.tools.make_get_weather_coroutine` — httpx mockeado

| Test | Qué verifica |
|------|--------------|
| `test_get_weather_returns_structured_result` | 6 campos: city, temperature_c, feels_like_c, description, humidity_pct, precipitation_mm |
| `test_get_weather_hot_city` | Sevilla 38°C → valores correctos |
| `test_get_weather_cold_city` | Reikiavik -5°C/nieve → valores negativos correctos |
| `test_get_weather_timeout_returns_error_json` | `httpx.HTTPError` → error JSON con nombre ciudad |
| `test_get_weather_missing_key_returns_error_json` | Respuesta sin `current_condition` → error JSON |
| `test_get_weather_empty_condition_list_returns_error` | `current_condition: []` → IndexError → error JSON |
| `test_get_weather_city_name_url_encoded` | "San Sebastián" (tildes+espacio) → sin crash |

**Resultado:** `Ran 7 tests — OK`

---

### 20. `TestRecommenderPackingTool` _(rama: `tests_recommender`)_
**Módulo:** `app.agents.recommender.tools.make_get_packing_items_coroutine`

| Test | Qué verifica |
|------|--------------|
| `test_packing_items_reads_real_csv` | Lee `objetos.csv` real → items de ropa y electrónica |
| `test_packing_items_count_matches_csv` | `total == len(items)` |
| `test_packing_items_no_empty_entries` | Ningún item es string vacío |
| `test_packing_items_csv_not_found_returns_error` | CSV inexistente → error JSON (OSError) |
| `test_packing_items_empty_csv_returns_error` | CSV vacío → error JSON |
| `test_packing_items_returns_non_ascii_correctly` | Tildes y ñ preservadas (`ensure_ascii=False`) |

**Resultado:** `Ran 6 tests — OK`

---

### 21. `TestRecommenderPrompt` _(rama: `tests_recommender`)_
**Módulo:** `app.agents.recommender.prompts.get_recommender_system_prompt` — función pura

| Test | Qué verifica |
|------|--------------|
| `test_prompt_contains_tools_section` | Sección TOOLS presente |
| `test_prompt_contains_output_format_section` | Sección OUTPUT FORMAT presente |
| `test_prompt_contains_classification_rules_section` | Sección CLASSIFICATION RULES presente |
| `test_prompt_mentions_get_weather_tool` | `get_weather` nombrado en el prompt |
| `test_prompt_mentions_get_packing_items_tool` | `get_packing_items` nombrado |
| `test_prompt_mentions_obligatorios_category` | Categoría OBLIGATORIOS presente |
| `test_prompt_mentions_recomendados_category` | Categoría RECOMENDADOS presente |
| `test_prompt_mentions_descartados_category` | Categoría DESCARTADOS presente |
| `test_prompt_instructs_tool_call_order` | `get_weather` aparece antes de `get_packing_items` en el texto |
| `test_prompt_instructs_language_matching` | Instruye responder en el idioma del usuario |
| `test_prompt_forbids_inventing_items` | Prohíbe inventar items fuera de la lista |
| `test_prompt_contains_current_date` | Contiene el año actual (fecha inyectada en runtime) |
| `test_prompt_is_non_empty_string` | String no vacío de > 100 chars |

**Resultado:** `Ran 13 tests — OK`

---

## Resumen de cobertura total

| Categoría | Clases | Tests | Rama |
|-----------|--------|-------|------|
| Guardrails de entrada | 2 | 24 | main |
| Guardrail de salida | 1 | 5 | main |
| Memoria (detección + contexto) | 2 | 10 | main |
| Persistencia (gastos + recordatorios) | 2 | 6 | main |
| Enrutamiento Supervisor (live LLM) | 1 | 8 | main |
| Telegram chunking | 1 | 6 | main |
| Directivas de agente | 1 | 7 | main |
| Concurrencia del orquestador | 1 | 1 | main |
| Poda de historial | 1 | 1 | main |
| Brave Search + travel_search tool | 2 | 16 | tests_brave |
| RAG (texto puro + query + PDFs + status) | 4 | 46 | tests_rag |
| Recommender (weather + packing + prompt) | 3 | 26 | tests_recommender |
| **TOTAL** | **21** | **156** | |
