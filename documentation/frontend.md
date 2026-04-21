# Interfaz Web del Travel Assistant

## Descripción

La interfaz web es una aplicación frontend simple desarrollada con HTML5, CSS3 y JavaScript vanilla que permite interactuar con el backend del Travel Assistant a través de su API REST.

## Ubicación de archivos

```
app/frontend/
├── index.html      # Página principal
└── app.js          # Lógica de interacción
```

## Características

### Funcionalidades disponibles
- **Estado del sistema**: Visualización del estado de LLM, RAG, MCP y base de datos
- **Gestión financiera**: Consulta de gastos registrados
- **Recordatorios**: Lista de recordatorios activos
- **Testing LLM**: Pruebas directas del modelo de lenguaje
- **Herramientas MCP**: Lista y ejecución de herramientas disponibles
- **Mensajería**: Envío de mensajes al sistema de procesamiento
- **Consulta documental**: Búsqueda en documentos normativos (.txt y .pdf)

### Interfaz de usuario
- Diseño responsive y minimalista
- Navegación por pestañas
- Formularios intuitivos
- Visualización clara de respuestas JSON
- Indicadores de estado en tiempo real

## Endpoints utilizados

### Estado y consultas
- `GET /status` - Estado completo del sistema
- `GET /expenses` - Lista de gastos
- `GET /reminders` - Lista de recordatorios
- `GET /mcp/tools` - Herramientas MCP disponibles

### Acciones
- `POST /message` - Procesamiento de mensajes de usuario
- `POST /llm/test` - Testing directo del LLM
- `POST /mcp/execute` - Ejecución de herramientas MCP

## Estructura del código

### index.html
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Travel Assistant</title>
    <style>
        /* Estilos CSS inline para simplicidad */
    </style>
</head>
<body>
    <div class="container">
        <h1>Travel Assistant</h1>

        <!-- Navegación por pestañas -->
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('status')">Estado</button>
            <button class="tab-button" onclick="showTab('expenses')">Gastos</button>
            <button class="tab-button" onclick="showTab('reminders')">Recordatorios</button>
            <button class="tab-button" onclick="showTab('llm')">Test LLM</button>
            <button class="tab-button" onclick="showTab('mcp')">MCP Tools</button>
            <button class="tab-button" onclick="showTab('message')">Mensaje</button>
        </div>

        <!-- Contenido de las pestañas -->
        <div id="status" class="tab-content active">
            <!-- Estado del sistema -->
        </div>

        <div id="expenses" class="tab-content">
            <!-- Gestión de gastos -->
        </div>

        <!-- Más pestañas... -->
    </div>

    <script src="app.js"></script>
</body>
</html>
```

### app.js - Funciones principales

#### Gestión de pestañas
```javascript
function showTab(tabName) {
    // Ocultar todas las pestañas
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Mostrar la pestaña seleccionada
    const selectedTab = document.getElementById(tabName);
    selectedTab.classList.add('active');

    // Actualizar botones de pestaña
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(button => button.classList.remove('active'));
    event.target.classList.add('active');
}
```

#### Comunicación con API
```javascript
async function apiCall(endpoint, method = 'GET', data = null) {
    const config = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (data) {
        config.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, config);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API call failed:', error);
        return { error: error.message };
    }
}
```

#### Testing del LLM
```javascript
async function testLLM() {
    const text = document.getElementById('llm-input').value;
    if (!text.trim()) {
        alert('Por favor ingresa un texto para testear');
        return;
    }

    const result = await apiCall('/llm/test', 'POST', { text: text });
    displayResult('llm-result', result);
}
```

## Flujo de uso

1. **Inicio**: Abrir `http://127.0.0.1:8000/app` en el navegador
2. **Estado del sistema**: Verificar que todos los servicios estén operativos
3. **Testing**: Probar funcionalidades individuales
4. **Interacción**: Enviar mensajes y ver respuestas

## Consideraciones técnicas

### CORS
- El backend FastAPI maneja automáticamente CORS para desarrollo
- En producción, configurar CORS apropiadamente

### Seguridad
- Validación de inputs en el frontend
- Sanitización de datos antes de envío
- Manejo seguro de errores

### Rendimiento
- Llamadas asíncronas para no bloquear la UI
- Loading indicators para operaciones largas
- Cache de resultados cuando apropiado

## Testing y debugging

### Consola del navegador
```javascript
// Ver estado de la API
apiCall('/status').then(console.log);

// Test de mensaje
apiCall('/message', 'POST', { text: 'Hola' }).then(console.log);
```

### Debugging de red
- Usar las herramientas de desarrollo del navegador
- Verificar requests/responses en la pestaña Network
- Revisar errores en Console

## Limitaciones actuales

- **Interfaz básica**: Diseño minimalista enfocado en funcionalidad
- **Sin autenticación**: No implementada para este prototipo
- **Cliente único**: No maneja múltiples usuarios concurrentes
- **Sin persistencia de sesión**: Estado se pierde al recargar

## Mejoras futuras planificadas

- **UI/UX mejorada**: Diseño más moderno con framework CSS
- **Autenticación**: Sistema de usuarios
- **Tiempo real**: WebSockets para actualizaciones live
- **PWA**: Funcionalidad offline
- **Testing**: Cobertura de tests automatizados
- **Documentación**: Guías de usuario detalladas

## Integración con el backend

La interfaz web consume la misma API que el bot de Telegram, asegurando consistencia en la funcionalidad. Todos los endpoints están documentados en la especificación OpenAPI generada automáticamente por FastAPI (disponible en `/docs`).

## Buenas prácticas seguidas

- Separación de capas: API, orquestador, servicios y frontend.
- Frontend estático sencillo y desacoplado del backend.
- El backend sirve la app en un único punto de entrada (`/app`) y expone la API REST en rutas separadas.
