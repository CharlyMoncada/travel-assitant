# Interfaz Web del Travel Assistant

## Descripción

La interfaz web del Travel Assistant es una consola minimalista e intuitiva desarrollada en JavaScript vanilla, HTML5 y CSS3. Su propósito principal es servir como panel interactivo para el control, monitorización y testing rápido de las APIs y capacidades del asistente de viaje (incluyendo el estado de salud, consulta directa de base de datos relacional y comunicación interactiva con el agente multiserver).

---

## Ubicación de los Archivos en la Capa de Frontend

Los archivos estáticos del frontend se localizan en la ruta `/app/frontend/` y son servidos por FastAPI mediante la ruta estática `/static` y el endpoint `/app`:

```
app/frontend/
├── index.html      # Estructura del panel de control y consola de chat
├── app.js          # Lógica interactiva y llamadas fetch asíncronas
└── styles.css      # Hoja de estilos mínimos del panel
```

---

## Características de la Interfaz Real

### 1. Monitorización en Tiempo Real
- **Ver Estado (`GET /status`)**: Muestra de forma inmediata un reporte estructurado en JSON sobre el estado del sistema, incluyendo la conectividad del bot de Telegram, el estado de ChromaDB (RAG), el LLM OpenAI, el archivo físico SQLite y el estado particular en línea de ambos servidores MCP desacoplados (puertos 8002 y 8003).

### 2. Acceso Directo de Datos Relacionales
- **Ver Gastos (`GET /expenses`)**: Consulta en crudo y de manera instantánea el resumen financiero guardado en la base de datos (monto total acumulado, desglose por categorías y transacciones).
- **Ver Recordatorios (`GET /reminders`)**: Lista la agenda activa del viajero obtenida directamente de SQLite.

### 3. Descubrimiento Dinámico
- **Ver Herramientas MCP (`GET /mcp/tools`)**: Expone el catálogo rico de herramientas disponibles consultado al vuelo en los servidores de finanzas y recordatorios.

### 4. Consola del Agente
- **Enviar Mensaje (`POST /message`)**: Permite entablar diálogos e instruir comandos al asistente. Genera un identificador de sesión único (`session_id`) autogestionado en el `localStorage` del navegador, garantizando que el checkpointer conversacional mantenga la memoria consistente entre turnos.

---

## Endpoints Consumidos por la Interfaz

La aplicación se comunica de forma asíncrona con el backend mediante las siguientes rutas:

| Método | Endpoint | Payload esperado | Propósito de Uso |
| :--- | :--- | :--- | :--- |
| **`GET`** | `/status` | *(Ninguno)* | Obtener estado de salud y telemetría de submódulos. |
| **`GET`** | `/expenses` | *(Ninguno)* | Obtener el sumario financiero actual. |
| **`GET`** | `/reminders` | *(Ninguno)* | Listar tareas e itinerario de viaje. |
| **`GET`** | `/mcp/tools` | *(Ninguno)* | Listar herramientas MCP cargadas dinámicamente. |
| **`POST`** | `/message` | `{"text": "...", "thread_id": "..."}` | Enviar mensaje al agente persistiendo el hilo de conversación. |

---

## Estructura de Código Real de la Interfaz

### 1. index.html (`app/frontend/index.html`)

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Travel Assistant UI</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <header>
    <h1>Travel Assistant</h1>
    <p>Interfaz mínima para consumir la API del asistente de viaje.</p>
  </header>

  <section class="panel">
    <button id="statusButton">Ver estado</button>
    <button id="expensesButton">Ver gastos</button>
    <button id="remindersButton">Ver recordatorios</button>
    <button id="toolsButton">Ver herramientas MCP</button>
  </section>

  <section class="panel">
    <label for="messageInput">Enviar mensaje a `/message`</label>
    <textarea id="messageInput" rows="3" placeholder="Escribe aquí tu mensaje..."></textarea>
    <button id="sendMessageButton">Enviar mensaje</button>
  </section>

  <section class="results">
    <h2>Resultado</h2>
    <pre id="resultOutput">Presiona un botón para ver los datos.</pre>
  </section>

  <script src="/static/app.js"></script>
</body>
</html>
```

### 2. app.js (`app/frontend/app.js`)

```javascript
const resultOutput = document.getElementById('resultOutput');
const messageInput = document.getElementById('messageInput');

// Obtener o crear un session_id en localStorage para mantener el estado de la sesión
let sessionId = localStorage.getItem('travel_assistant_session_id');
if (!sessionId) {
  sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
  localStorage.setItem('travel_assistant_session_id', sessionId);
}

const setResult = (data) => {
  resultOutput.textContent = JSON.stringify(data, null, 2);
};

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  const data = await response.json();
  setResult(data);
  return data;
};

document.getElementById('statusButton').addEventListener('click', () => {
  requestJson('/status');
});

document.getElementById('expensesButton').addEventListener('click', () => {
  requestJson('/expenses');
});

document.getElementById('remindersButton').addEventListener('click', () => {
  requestJson('/reminders');
});

document.getElementById('toolsButton').addEventListener('click', () => {
  requestJson('/mcp/tools');
});

document.getElementById('sendMessageButton').addEventListener('click', async () => {
  const text = messageInput.value.trim();
  if (!text) {
    setResult({ error: 'Escribe un mensaje antes de enviar.' });
    return;
  }
  await requestJson('/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, thread_id: sessionId }),
  });
});
```

---

## Flujo de Uso Recomendado en Pruebas

1. **Verificación Inicial**: Iniciar los servidores e ingresar a `http://localhost:8000/app` en el navegador.
2. **Chequeo de Salud**: Presionar **Ver estado** y corroborar que el campo `mcp.online` figure como `true`.
3. **Consulta de Gastos**: Presionar **Ver gastos** para comprobar la carga de SQLite.
4. **Envío de Mensajes**: Enviar un mensaje de diálogo conversacional en la consola para comprobar la inferencia semántica del Supervisor LLM y el desvío correcto al agente de especialidad.
