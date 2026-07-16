# Docker y Gestión de Datos Persistentes

## Resumen

Este documento describe cómo está organizada la persistencia de datos del Travel Assistant en entornos Docker y locales, los problemas encontrados en el despliegue original y las correcciones aplicadas en la rama `fix_data`.

---

## Problema original

El `docker-compose.yml` intentaba montar el fichero de base de datos con la ruta:

```yaml
volumes:
  - ./data/travel_assistant.db:/code/travel_assistant.db
```

Sin embargo, el directorio `data/` **no existía** en el repositorio, lo que provocaba que Docker creara un directorio vacío en lugar de un fichero, y la aplicación arrancaba sin base de datos operativa o fallaba silenciosamente al intentar escribir en SQLite.

Adicionalmente, el índice vectorial de ChromaDB (`app/chromadb_store/`) no tenía volumen persistente en Docker, por lo que se re-indexaban todos los documentos PDF/TXT en cada arranque del contenedor, aumentando el tiempo de startup sin necesidad.

---

## Arquitectura de datos tras la corrección

### Directorio `data/`

Todos los ficheros de datos persistentes en tiempo de ejecución se ubican bajo `data/` en la raíz del proyecto:

```
travel-assitant/
├── data/
│   ├── .gitkeep          ← garantiza que el directorio existe en git
│   └── travel_assistant.db  ← generada en runtime, ignorada por git
├── app/
│   └── chromadb_store/   ← generada en runtime, ignorada por git
└── ...
```

### Base de datos SQLite

| Entorno | Ruta en el sistema de ficheros | Modo de acceso |
|---------|-------------------------------|----------------|
| **Local** | `data/travel_assistant.db` | Ruta relativa al CWD del proceso Python |
| **Docker** | `/code/data/travel_assistant.db` | Montada desde el host vía volume bind |

La URL de SQLAlchemy en `app/services/persistence/db.py`:

```python
DATABASE_URL = "sqlite:///data/travel_assistant.db"
```

Los tres slashes (`///`) indican ruta relativa al directorio de trabajo actual. En local, ese directorio es la raíz del proyecto. En Docker, el `WORKDIR` es `/code`, por lo que la ruta efectiva es `/code/data/travel_assistant.db`.

### ChromaDB (índice vectorial RAG)

ChromaDB persiste su índice en `app/chromadb_store/`. En Docker se gestiona mediante un **named volume** de Docker (`chromadb_data`), lo que garantiza que el índice sobrevive reinicios y actualizaciones de imagen sin necesidad de re-indexar los documentos PDF.

---

## Configuración Docker Compose

### Servicios y volúmenes

```yaml
services:
  web:
    volumes:
      - ./data:/code/data              # bind mount: directorio data/ completo
      - chromadb_data:/code/app/chromadb_store  # named volume: índice RAG persistente

  finance:
    volumes:
      - ./data:/code/data              # la DB de gastos es la misma SQLite compartida

  reminder:
    volumes:
      - ./data:/code/data              # la DB de recordatorios es la misma SQLite compartida

volumes:
  chromadb_data:                       # volumen gestionado por Docker Engine
```

### Por qué montar `./data` completo en lugar de solo el fichero `.db`

Montar el **directorio** en lugar del fichero individual ofrece varias ventajas:

1. **No requiere que el fichero exista antes del primer arranque**: Docker crea el directorio si no existe; SQLite crea el fichero `.db` al primer `init_db()`.
2. **Permite añadir futuras bases de datos** sin modificar `docker-compose.yml`.
3. **Evita el bug original**: montar un fichero que no existe convierte el mount en un directorio vacío.

---

## Ficheros ignorados en git y en Docker

### `.gitignore`

```
travel_assistant.db   ← legacy, para entornos sin data/
data/*.db             ← ignora la DB bajo el nuevo directorio
app/chromadb_store/   ← índice vectorial generado en runtime
```

El fichero `data/.gitkeep` **sí** se incluye en git para garantizar que el directorio `data/` existe al clonar el repositorio.

### `.dockerignore`

```
*.db
*.sqlite3
data/                 ← no se copia la DB del host en la imagen
chromadb_store/       ← no se copia el índice del host en la imagen
```

La imagen Docker queda limpia de datos de runtime; estos se proveen exclusivamente a través de los volúmenes definidos en `docker-compose.yml`.

---

## Flujo de primer arranque con Docker

```
docker compose up --build
        │
        ▼
  Se construye la imagen
  (COPY . /code, sin data/ ni chromadb_store/)
        │
        ▼
  Se arranca el servicio web
  Monta ./data → /code/data  (directorio vacío en primer arranque)
        │
        ▼
  app/main.py → init_db()
  SQLite crea /code/data/travel_assistant.db
        │
        ▼
  app/main.py → init_rag()
  ChromaDB indexa los PDFs/TXTs de rag_docs/
  y persiste en el named volume chromadb_data
        │
        ▼
  Servicios finance y reminder arrancan
  Ambos montan ./data → /code/data
  Comparten la misma travel_assistant.db
```

En reinicios posteriores (`docker compose restart`), la base de datos ya existe en `./data/` y ChromaDB carga el índice del named volume sin re-indexar.

---

## Migración desde versión anterior

Si se tenía la aplicación corriendo localmente con la DB en la raíz del proyecto, se debe mover el fichero:

```bash
mv travel_assistant.db data/travel_assistant.db
```

Si se está en Docker y se quiere conservar datos anteriores, copiar manualmente la DB al directorio `data/` antes de arrancar.

---

## Comandos de referencia

```bash
# Primer arranque (construye imagen y levanta todos los servicios)
docker compose up --build

# Arranque rápido (sin reconstruir imagen)
docker compose up

# Parar sin borrar volúmenes
docker compose stop

# Parar y eliminar contenedores (los volúmenes se conservan)
docker compose down

# Parar, eliminar contenedores Y volúmenes (PÉRDIDA DE DATOS)
docker compose down -v

# Ver logs en tiempo real
docker compose logs -f web

# Acceder a la DB desde el host
sqlite3 data/travel_assistant.db ".tables"
```

---

## Rama y ficheros modificados

| Fichero | Cambio |
|---------|--------|
| `app/services/persistence/db.py` | `DATABASE_URL` → `sqlite:///data/travel_assistant.db` |
| `docker-compose.yml` | Volúmenes: bind mount `./data`, named volume `chromadb_data` |
| `.gitignore` | Añadido `data/*.db` |
| `.dockerignore` | Añadido `data/` |
| `scratch/query_db.py` | Ruta DB → `data/travel_assistant.db` |
| `data/.gitkeep` | Fichero nuevo para rastrear el directorio en git |
