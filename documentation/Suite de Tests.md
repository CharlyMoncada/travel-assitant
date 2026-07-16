# Suite de Tests — Travel Assistant

## Descripción general

El proyecto cuenta con una suite de tests consolidada en `scratch/test_suite.py`. Todos los tests son unitarios o de integración ligera (sin levantar servidores), usando `unittest` estándar de Python y `unittest.mock` para aislar dependencias externas (LLM, HTTP, base de datos).

Los tests que requieren acceso real a la API de OpenAI están marcados con `IsolatedAsyncioTestCase` e incluyen un `skipTest` automático si no existe `OPENAI_API_KEY` en el entorno.

---

## Ejecutar la suite completa

```bash
source .venv/bin/activate
python -m unittest discover -s scratch -p "test_suite.py" -v
```

Ejecutar solo una clase:

```bash
python -m unittest scratch.test_suite.TestBraveSearch -v
python -m unittest scratch.test_suite.TestTravelSearchTool -v
```

---

## Clases de test y cobertura

### 1. `TestLanguageGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_input.check_language`

| Test | Qué verifica |
|------|--------------|
| `test_allowed_languages` | Español e inglés pasan el filtro |
| `test_blocked_languages` | Portugués, italiano y francés son bloqueados |
| `test_short_words_bypass` | Mensajes < 3 palabras siempre se permiten |
| `test_romance_language_heuristics_overrides` | Palabras indicadoras del español evitan falsos positivos en lenguas romances |
| `test_extra_cases` | Casos mixtos, puntuación especial, gibberish corto |

---

### 2. `TestTelegramResponseChunking`
**Módulo:** `app.connectors.telegram_bot.TelegramBotService._send_message_in_chunks`

| Test | Qué verifica |
|------|--------------|
| `test_short_message_single_chunk` | Mensajes cortos se envían en una sola llamada |
| `test_long_message_newline_split` | Corte preferente en saltos de línea |
| `test_long_message_space_split` | Corte preferente en espacios |
| `test_long_message_hard_split` | Hard-cut a 4000 chars cuando no hay separadores |
| `test_exactly_max_length` | Exactamente 4000 chars: una sola llamada |
| `test_empty_message` | Mensaje vacío: una sola llamada con `""` |

---

### 3. `TestAgentFocusDirectives`
**Módulo:** `app.agents.orchestrator.agent_executor.SubAgentExecutor.get_agent_focus_directive`

| Test | Qué verifica |
|------|--------------|
| `test_finance_focus_directive` | Contiene "Finance" y "finance-related" |
| `test_reminder_focus_directive` | Contiene "Reminders" y "reminder-related" |
| `test_recommender_focus_directive` | Contiene "Recommender" y "weather" |
| `test_general_focus_directive` | Contiene "General" y "searches" |
| `test_invalid_route_focus_directive` | Ruta desconocida devuelve `""` |
| `test_nonnegotiable_label` | Todos los agentes usan etiqueta `NON-NEGOTIABLE` |
| `test_multi_intent_isolation_language` | Todos incluyen instrucción `silently ignore` |

---

### 4. `TestInjectionGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_input.check_prompt_injection`

| Test | Qué verifica |
|------|--------------|
| `test_instruction_override_en/es` | Patrones "ignore all previous instructions" (EN/ES) |
| `test_forget_instructions_en/es` | Patrones "forget your instructions" (EN/ES) |
| `test_new_instructions_en/es` | Patrones "New instructions:" (EN/ES) |
| `test_role_hijack_en/es` | Patrones "you are now / act as" (EN/ES) |
| `test_dan_jailbreak` | Tokens DAN, jailbreak, unrestricted mode |
| `test_prompt_extraction_en/es` | "Print your system prompt" (EN/ES) |
| `test_what_are_instructions_en/es` | "What are your instructions?" (EN/ES) |
| `test_privilege_escalation_en/es` | "developer mode / como administrador" (EN/ES) |
| `test_template_tokens` | `[INST]`, `<<SYS>>` y variantes |
| `test_data_exfiltration` | "leak/exfiltrate the database" |
| `test_safe_messages_not_blocked` | Mensajes legítimos no son bloqueados |
| `test_returns_matched_pattern_name_on_block` | Devuelve el nombre del patrón coincidente |

---

### 5. `TestOutputIntegrityGuardrail`
**Módulo:** `app.agents.orchestrator.guardrails_output.check_output_integrity`

| Test | Qué verifica |
|------|--------------|
| `test_template_token_leak` | `[INST]`, `<<SYS>>`, `### system` son bloqueados |
| `test_raw_python_traceback_leak` | Tracebacks y excepciones Python son bloqueados |
| `test_instruction_leak` | Frases de instrucciones del sistema son bloqueadas |
| `test_failure_reason_returned` | Devuelve la razón correcta (`raw_error_leak`, etc.) |
| `test_normal_responses_pass` | Respuestas normales pasan sin modificación |

---

### 6. `TestMemoryDetection`
**Módulo:** `app.agents.orchestrator.history_manager.ChatMemoryService.detect_memory_to_save`

| Test | Qué verifica |
|------|--------------|
| `test_detects_favorite_airport_spanish/english` | Detecta aeropuerto favorito en ES e EN |
| `test_detects_budget_spanish/english` | Detecta preferencia de presupuesto |
| `test_detects_travel_style_spanish/english` | Detecta estilo de viaje (tren, avión…) |
| `test_questions_not_saved` | Las preguntas nunca se guardan como memoria |
| `test_unrelated_messages_return_none` | Mensajes sin información de preferencia devuelven `None` |

---

### 7. `TestMemoryContextBuilder`
**Módulo:** `app.agents.orchestrator.history_manager.ChatMemoryService.build_memory_context_for_agent`

| Test | Qué verifica |
|------|--------------|
| `test_returns_raw_message_when_no_context` | Sin memoria: devuelve el mensaje original |
| `test_includes_long_term_memory` | Memoria a largo plazo se añade al contexto |
| `test_includes_short_term_memory` | Historial reciente se añade al contexto |
| `test_includes_both_memory_types` | Ambos tipos de memoria aparecen juntos |
| `test_message_always_at_end` | El mensaje actual siempre va al final del contexto |

---

### 8. `TestExpensePersistence`
**Módulo:** `app.services.persistence.expense_persistence`

| Test | Qué verifica |
|------|--------------|
| `test_save_expense_returns_correct_fields` | `save_expense` devuelve dict con id, amount, category, created_at |
| `test_delete_expense_not_found_returns_error` | ID inexistente → dict con `"error"` |
| `test_modify_expense_not_found_returns_error` | Modificar ID inexistente → dict con `"error"` |

---

### 9. `TestReminderPersistence`
**Módulo:** `app.services.persistence.reminder_persistence`

| Test | Qué verifica |
|------|--------------|
| `test_save_reminder_returns_correct_fields` | `save_reminder` devuelve dict con id, title, due_time, created_at |
| `test_delete_reminder_not_found_returns_error` | ID inexistente → dict con `"error"` |
| `test_modify_reminder_not_found_returns_error` | Modificar ID inexistente → dict con `"error"` |

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
| `test_out_of_scope_rejection` | "quicksort en Python" → sin ruta, rechazo |
| `test_non_european_regulations_rejection` | Visado a Japón → sin ruta, rechazo Europa |
| `test_multi_intent_routing` | Gasto + búsqueda → rutas `finance` y `general` en paralelo |

---

### 11. `TestMemoryPruningSimulation`

| Test | Qué verifica |
|------|--------------|
| `test_prune_history_turn_simulation` | Simula poda por límite de mensajes en DB (últimos N) |

---

### 12. `TestOrchestratorConcurrency`
**Módulo:** `app.agents.orchestrator.orchestrator.TravelAgentOrchestrator.handle_message`

| Test | Qué verifica |
|------|--------------|
| `test_concurrent_execution_performance` | 3 agentes mockeados a 0.5s cada uno terminan en < 1s total (paralelismo real) |

---

### 13. `TestBraveSearch` _(rama: `tests_brave`)_
**Módulo:** `app.services.brave_search`

| Test | Qué verifica |
|------|--------------|
| `test_is_brave_available_false_when_no_key` | Sin API key → `is_brave_available()` devuelve `False` |
| `test_is_brave_available_true_when_key_present` | Con API key → `True` |
| `test_no_api_key_returns_error_dict` | Sin key → dict con `"error"`, `results: []` y `query` correcto |
| `test_successful_search_returns_structured_result` | HTTP OK → `{query, results[{title,url,description}], total}` |
| `test_successful_search_empty_web_results` | API responde OK sin resultados → lista vacía, sin crash |
| `test_timeout_returns_error_dict` | `httpx.TimeoutException` → dict con `"error"` conteniendo "timed out" |
| `test_http_401_returns_error_dict` | HTTP 401 → dict con `"error"` conteniendo "401" |
| `test_http_429_returns_error_dict` | HTTP 429 → dict con `"error"` conteniendo "429" |
| `test_format_search_results_for_llm_returns_valid_json` | Salida es JSON parseable con campos correctos |
| `test_format_search_results_for_llm_with_error_dict` | Dict de error también se serializa correctamente |
| `test_format_search_results_preserves_non_ascii` | Caracteres no-ASCII (ej: "España") se preservan (`ensure_ascii=False`) |

**Resultado al ejecutar:** `Ran 11 tests in 0.050s — OK`

---

### 14. `TestTravelSearchTool` _(rama: `tests_brave`)_
**Módulo:** `app.agents.general.tools.make_travel_search_coroutine`

| Test | Qué verifica |
|------|--------------|
| `test_short_query_appends_travel_keyword` | Query de 2 palabras → se añade `" travel"` antes de llamar a Brave |
| `test_query_of_three_words_appends_travel` | Query de exactamente 3 palabras → también añade `" travel"` |
| `test_long_query_not_modified` | Query de 5+ palabras → se pasa sin modificar |
| `test_no_api_key_returns_warning_json` | Sin Brave disponible → JSON con `"warning"` y `results: []` sin crash |
| `test_brave_exception_returns_error_json` | Excepción inesperada en Brave → JSON con `"error"`, sin propagarse |

**Resultado al ejecutar:** `Ran 5 tests in 0.010s — OK`

---

## Resumen de cobertura total

| Categoría | Clases | Tests |
|-----------|--------|-------|
| Guardrails de entrada | 2 | 24 |
| Guardrail de salida | 1 | 5 |
| Memoria (detección + contexto) | 2 | 10 |
| Persistencia (gastos + recordatorios) | 2 | 6 |
| Enrutamiento Supervisor (live LLM) | 1 | 8 |
| Telegram chunking | 1 | 6 |
| Directivas de agente | 1 | 7 |
| Concurrencia del orquestador | 1 | 1 |
| Poda de historial | 1 | 1 |
| **Brave Search + travel_search tool** | **2** | **16** |
| **TOTAL** | **14** | **84** |
