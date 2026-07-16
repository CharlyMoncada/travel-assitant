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
python -m unittest scratch.test_suite.TestRAGTextProcessing -v
python -m unittest scratch.test_suite.TestRAGQueryLogic -v
python -m unittest scratch.test_suite.TestRAGPDFExtraction -v
python -m unittest scratch.test_suite.TestRAGStatus -v
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

### 13. `TestRAGTextProcessing` _(rama: `tests_rag`)_
**Módulo:** funciones puras de `app.services.rag` — sin ChromaDB, sin embeddings, sin LLM

| Test | Qué verifica |
|------|--------------|
| `test_normalize_strips_leading_trailing_whitespace` | Elimina espacios al inicio y final |
| `test_normalize_replaces_cr_with_newline` | `\r\n` → `\n` |
| `test_normalize_removes_soft_hyphen_at_line_end` | `-\n` (guion suave) → palabras se unen |
| `test_normalize_collapses_multiple_spaces` | Múltiples espacios → uno |
| `test_normalize_collapses_excess_blank_lines` | Más de 2 líneas en blanco → 2 |
| `test_normalize_empty_string_returns_empty` | `""` → `""` |
| `test_normalize_null_bytes_replaced` | `\x00` → espacio |
| `test_remove_noise_strips_urls` | URLs `https://` eliminadas |
| `test_remove_noise_strips_date_patterns` | Fechas `1/6/2024, 10:30 AM` eliminadas |
| `test_remove_noise_strips_your_europe_phrase` | Frase "Your Europe" eliminada |
| `test_remove_noise_strips_menu_keyword` | "MENÚ" eliminado |
| `test_remove_noise_preserves_meaningful_content` | Contenido real ("pasaporte válido") se conserva |
| `test_chunk_empty_string_returns_empty_list` | `""` → `[]` |
| `test_chunk_short_text_returns_single_chunk` | Texto corto → 1 chunk |
| `test_chunk_long_text_creates_multiple_chunks` | Texto > 900 chars → varios chunks |
| `test_chunk_no_duplicates` | Chunks resultantes son únicos |
| `test_chunk_all_content_covered` | Todos los chunks son no vacíos |
| `test_chunk_paragraph_boundaries_respected` | Párrafos cortos separados quedan en distintos chunks |
| `test_content_hash_returns_hex_string` | SHA-1 → 40 caracteres hexadecimales |
| `test_content_hash_same_input_same_output` | Determinismo: mismo input → mismo hash |
| `test_content_hash_different_inputs_differ` | Inputs distintos → hashes distintos |
| `test_last_words_returns_last_n` | Devuelve últimas N palabras |
| `test_last_words_shorter_than_n` | Texto más corto que N → todo el texto |
| `test_last_words_empty_string` | `""` → `""` |

**Resultado:** `Ran 24 tests — OK`

---

### 14. `TestRAGQueryLogic` _(rama: `tests_rag`)_
**Módulo:** `app.services.rag.query_normative_documents` (ChromaDB y LLM mockeados)

| Test | Qué verifica |
|------|--------------|
| `test_empty_query_returns_specific_message` | Query vacía → mensaje "La consulta está vacía." |
| `test_whitespace_only_query_returns_specific_message` | Query solo espacios → mismo mensaje |
| `test_no_close_results_returns_european_fallback_spanish` | Distancias > umbral + idioma ES → fallback europeo en español |
| `test_no_close_results_returns_european_fallback_english` | Distancias > umbral + idioma EN → fallback europeo en inglés |
| `test_good_results_calls_compose_rag_answer` | Distancias < umbral → `compose_rag_answer` se llama y su respuesta se devuelve |
| `test_good_results_sources_contain_score` | Cada fuente tiene campo `score` = `1 - distance` |
| `test_results_filtered_by_max_distance` | Chunks con distancia > MAX_DISTANCE se excluyen de `sources` |

**Resultado:** `Ran 7 tests — OK`

---

### 15. `TestRAGPDFExtraction` _(rama: `tests_rag`)_
**Módulo:** `app.services.rag._build_chunks_from_pdf_file` / `_build_chunks_from_text_file`  
Tests de integración con los ficheros reales de `rag_docs/`. Solo usa `pdfplumber` — sin ChromaDB ni embeddings.

| Test | Qué verifica |
|------|--------------|
| `test_txt_visa_produces_chunks` | `visa.txt` genera al menos 1 chunk |
| `test_txt_seguridad_chunk_has_expected_metadata` | Chunks de `seguridad.txt` tienen `type="text"` y source correcto |
| `test_txt_chunks_have_unique_ids` | IDs de chunks de TXT son únicos |
| `test_pdf_ciudadanos_ue_produces_chunks` | PDF "ciudadanos de la UE" genera al menos 1 chunk |
| `test_pdf_chunks_are_non_empty_strings` | Todos los chunks son strings no vacíos |
| `test_pdf_chunks_have_page_metadata` | Cada chunk tiene `page > 0` en metadata |
| `test_pdf_chunks_have_unique_ids` | IDs de chunks de PDF son únicos |
| `test_pdf_pasaportes_produces_chunks` | PDF de pasaportes genera chunks |
| `test_pdf_menores_produces_chunks` | PDF de menores genera chunks |
| `test_pdf_content_contains_travel_keywords` | Texto extraído contiene palabras clave de viaje |
| `test_pdf_chunk_size_within_bounds` | Ningún chunk supera `CHUNK_SIZE × 1.1` caracteres |

**Resultado:** `Ran 11 tests — OK`

---

### 16. `TestRAGStatus` _(rama: `tests_rag`)_
**Módulo:** `app.services.rag.rag_status`

| Test | Qué verifica |
|------|--------------|
| `test_rag_status_returns_all_expected_keys` | Devuelve exactamente los 8 campos esperados |
| `test_rag_status_document_count_matches_collection` | `document_count` coincide con `collection.count()` |
| `test_rag_status_collection_count_error_returns_none` | Si `count()` lanza excepción → `document_count` es `None`, sin crash |
| `test_rag_status_collection_name_correct` | `collection_name` coincide con la constante `COLLECTION_NAME` |

**Resultado:** `Ran 4 tests — OK`

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
| **RAG (texto puro + query logic + PDFs + status)** | **4** | **46** |
| **TOTAL** | **16** | **114** |

> **Nota:** Las clases `TestBraveSearch` y `TestTravelSearchTool` (16 tests adicionales) están en la rama `tests_brave` y se sumarán al fusionar con main, llevando el total a **18 clases y 130 tests**.
