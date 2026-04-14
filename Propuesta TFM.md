# **Propuesta de Trabajo Fin de Máster (TFM)**

**Título:** Sistema Agéntico de Asistencia al Viajero: Integración de MCP, RAG y Herramientas de Persistencia en Interfaces de Mensajería Instantánea.

## **1\. Descripción de la propuesta**

El proyecto consiste en el desarrollo de un asistente inteligente basado en IA Generativa diseñado para acompañar al usuario en todas las etapas de un viaje. La solución se despliega a través de canales de **mensajería instantánea** (WhatsApp, Telegram, etc.), actuando como una interfaz conversacional única que centraliza diversos servicios.

La arquitectura técnica se apoya en tres pilares:

1. **Model Context Protocol (MCP):** Para la conexión estandarizada con herramientas de búsqueda y bases de datos.  
2. **RAG (Retrieval-Augmented Generation):** Para el acceso a información normativa y turística veraz.  
3. **Orquestación de Agentes:** Para la gestión de flujos de trabajo complejos y persistencia de datos.

## **2\. Motivación del proyecto**

La planificación de viajes padece de una alta fragmentación. El usuario debe consultar múltiples fuentes para documentación, precios y control de gastos. El uso de **MCP** representa una innovación radical en la ingeniería de prompts y el uso de herramientas, ya que permite que el LLM interactúe con el mundo real de forma modular.

Este proyecto busca demostrar que es posible construir un "operador de viajes" personal que resida en el bolsillo del usuario, minimizando la fricción de entrada mediante el uso de interfaces de chat ya familiares, y garantizando la precisión de los datos mediante técnicas avanzadas de recuperación y ejecución de código.

## **3\. Objetivos finales (MVP de 4 funcionalidades)**

El objetivo general es validar la viabilidad de un asistente agéntico mediante la implementación de las siguientes capacidades core; cada una de las funcionalidades estará enfocada en una primera instancia a vuelos y para ser testeada en uno o dos países aún por definir:

* **Módulo de Consultoría Normativa (RAG):** Implementar un sistema de recuperación que permita al usuario consultar requisitos legales, visados y alertas sanitarias de cualquier destino. Se utilizará una base de datos vectorial para asegurar que las respuestas se basen en documentos oficiales y no en alucinaciones del modelo.  
* **Buscador Logístico en Tiempo Real (MCP \+ Tools):** Desarrollar la capacidad del asistente para conectarse a APIs externas de vuelos y alojamiento. Mediante el protocolo MCP, el asistente podrá realizar búsquedas activas y comparar opciones vigentes según los criterios del usuario.  
* **Gestor de Finanzas del Viajero (Persistencia):** Crear una herramienta de registro de gastos en lenguaje natural. El sistema deberá ser capaz de procesar entradas como *"Anota 20€ en transporte"*, almacenarlas en una base de datos estructurada y generar reportes de presupuesto bajo demanda.  
* **Agente de Itinerario y Recordatorios:** Implementar una lógica de gestión temporal que permita al usuario delegar recordatorios críticos (vuelos, check-ins, trenes). El sistema enviará notificaciones proactivas a la plataforma de mensajería para asistir al usuario en tiempo real durante su trayecto.

