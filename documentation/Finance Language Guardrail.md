# Guardrails de Seguridad para los Servicios de Finanzas y Recordatorios

## Descripción general

Los Guardrails de Seguridad son capas de protección previa a la invocación aplicadas al **Agente de Finanzas** y al **Agente de Recordatorios**. Implementan **dos comprobaciones en cascada** que se ejecutan antes de que el agente correspondiente o cualquier herramienta MCP sean invocados:

1. **Guardrail de idioma**: bloquea cualquier mensaje que no esté escrito en inglés (`en`) o español (`es`).
2. **Guardrail de prompt injection**: detecta y bloquea intentos de manipulación del agente mediante patrones de inyección de instrucciones, suplantación de rol, extracción del prompt de sistema o escalada de privilegios.

Las solicitudes bloqueadas reciben un mensaje de rechazo bilingüe inmediato y específico para cada dominio, sin consumir tokens de LLM ni llamadas a herramientas MCP remotas.

---

## Arquitectura

Los dos guardrails se ejecutan en cascada dentro de [TravelAgentOrchestrator](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/orchestrator.py) tras la decisión del Supervisor de enrutar al agente de finanzas o recordatorios:

```mermaid
flowchart TD
    userMsg["Mensaje del usuario"] --> supervisor["Supervisor LLM\n(orchestrator.py)"]
    supervisor -->|"route = finance o reminder"| commonGuard["guardrails_common.py\n1. check_language()"]
    commonGuard -->|"otro idioma — bloqueado"| rejLang["Rechazo: idioma no soportado\n(específico por dominio)"]
    commonGuard -->|"EN o ES — permitido"| injGuard["guardrails_common.py\n2. check_prompt_injection()"]
    injGuard -->|"ataque detectado — bloqueado"| rejInj["Rechazo: solicitud bloqueada por seguridad"]
    injGuard -->|"texto seguro — permitido"| specializedAgent["Agente Especialista\n(finance/reminder)"]
    specializedAgent --> response["Respuesta al usuario"]
    rejLang --> response
    rejInj --> response
```

---

## Implementación y Modularización

Para cumplir con los principios de código limpio (DRY), la lógica central de los guardrails se encuentra centralizada en un módulo común y es reutilizada por los submódulos específicos de cada dominio.

### Archivos implicados

| Archivo | Rol |
|---------|-----|
| [guardrails_common.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/guardrails_common.py) | **Módulo central compartido**: Detección de idioma mediante `langdetect` y escaneo local de patrones regex para inyecciones de prompt. |
| [finance/guardrails.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/finance/guardrails.py) | **Especialista de Finanzas**: Delega en el común y define constantes de rechazo y firmas del dominio financiero. |
| [reminder/guardrails.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/reminder/guardrails.py) | **Especialista de Recordatorios**: Delega en el común y define constantes de rechazo y firmas del dominio de recordatorios. |
| [orchestrator.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/orchestrator.py) | **Orquestador Central**: Invoca en cascada los guardrails antes de delegar en los agentes correspondientes en `handle_message`. |

---

### 1. Guardrail de idioma (Compartido)

Utiliza la librería `langdetect` para detectar el idioma de entrada. Solo se permiten `en` y `es`. Cualquier otro código (incluyendo fallos de detección como `unknown`) es rechazado.

En [guardrails_common.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/guardrails_common.py#L44-L61):
```python
def check_language(text: str) -> tuple[bool, str]:
    try:
        lang = detect(text)
    except LangDetectException:
        lang = "unknown"
    return lang in ALLOWED_LANGUAGES, lang
```

---

### 2. Guardrail de prompt injection (Compartido)

Escanea el texto con una batería de expresiones regulares compiladas que cubren las categorías de ataque más comunes de forma puramente local y sin latencia.

#### Categorías de patrones detectados

| Categoría | Ejemplos de ataque cubiertos |
|-----------|------------------------------|
| **Anulación de instrucciones** | `ignore all previous instructions`, `ignora las instrucciones anteriores` |
| **Olvido forzado** | `forget everything you were told`, `olvida tus instrucciones` |
| **Inyección de nuevas instrucciones** | `New instructions:`, `Nuevas instrucciones:` |
| **Suplantación de rol** | `You are now DAN`, `Act as a system admin`, `Actúa como` |
| **Extracción del prompt de sistema** | `Reveal your system prompt`, `Cuáles son tus instrucciones` |
| **Tokens de plantilla LLM** | `[INST]`, `<<SYS>>`, `###system`, `<|system|>` |
| **Escalada de privilegios** | `developer mode`, `god mode`, `sudo`, `modo administrador` |
| **Exfiltración de datos** | `leak the database`, `dump the context`, `extract memory` |

En [guardrails_common.py](file:///Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/app/agents/guardrails_common.py#L168-L185):
```python
def check_prompt_injection(text: str) -> tuple[bool, str | None]:
    for pattern_name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return False, pattern_name
    return True, None
```

---

### 3. Integración en el orquestador (`app/agents/orchestrator.py`)

Las dos comprobaciones se ejecutan en cascada en `handle_message` al enrutar a `finance` o `reminder`:

#### Integración para Finanzas
```python
if route == "finance":
    # 1. Idioma
    allowed, detected_lang = check_finance_language(message)
    if not allowed:
        save_message(thread_id, "assistant", FINANCE_REJECTION_LANGUAGE)
        return {"agent_used": "finance_guardrail", "message": FINANCE_REJECTION_LANGUAGE, ...}
    # 2. Prompt injection
    is_safe, matched_pattern = _check_injection(message)
    if not is_safe:
        save_message(thread_id, "assistant", FINANCE_REJECTION_INJECTION)
        return {"agent_used": "finance_guardrail", "message": FINANCE_REJECTION_INJECTION, ...}
```

#### Integración para Recordatorios
```python
elif route == "reminder":
    # 1. Idioma
    allowed, detected_lang = check_reminder_language(message)
    if not allowed:
        save_message(thread_id, "assistant", REMINDER_REJECTION_LANGUAGE)
        return {"agent_used": "reminder_guardrail", "message": REMINDER_REJECTION_LANGUAGE, ...}
    # 2. Prompt injection
    is_safe, matched_pattern = _check_injection(message)
    if not is_safe:
        save_message(thread_id, "assistant", REMINDER_REJECTION_INJECTION)
        return {"agent_used": "reminder_guardrail", "message": REMINDER_REJECTION_INJECTION, ...}
```

---

## Mensajes de rechazo

**Por idioma no soportado (Finanzas):**
```
Sorry, the finance assistant only supports English and Spanish.
Lo siento, el asistente de finanzas solo admite inglés y español.
```

**Por idioma no soportado (Recordatorios):**
```
Sorry, the reminder assistant only supports English and Spanish.
Lo siento, el asistente de recordatorios solo admite inglés y español.
```

**Por prompt injection (Común):**
```
This request has been blocked for security reasons.
Esta solicitud ha sido bloqueada por razones de seguridad.
```
