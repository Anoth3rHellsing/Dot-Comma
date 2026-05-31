# Dot-Comma
Daily task manager for messy people

## Installation Guide (English)

To set up and run the application, follow these steps:

1. **Install dependencies:**
   Make sure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database:**
   Run the following command to create the required SQLite database (`database.db`):
   ```bash
   python init_db.py
   ```

3. **Start the server:**
   Start the Flask application by running:
   ```bash
   python app.py
   ```
   The application will be accessible via your web browser.

## Introduction to D.O.T.

D.O.T. (formerly Dot & Comma) is a daily task manager centered around Sprint and Scrum methodologies. It is designed to help users track progress, set daily goals, and identify impediments through a 15-minute daily AI stand-up.

### Features
* **AI Stand-up:** A daily 15-minute check-in with "Dot", the AI assistant, to track progress and manage tasks.
* **Retro 80s Aesthetic:** The application's visual design strictly adheres to an 80s CRT monitor aesthetic (featuring scanlines, screen flicker, phosphor glow, and a DOS-style boot screen), combined with refined structural styling.
* **Persistent Chat:** AI communication and notifications are handled via an in-page persistent chat interface, saving conversations to the database.

### Tech Stack
* **Backend:** Python, Flask
* **Frontend:** Vanilla HTML, CSS, JavaScript
* **Database:** SQLite (Stored persistently in the system's AppData directory)
* **AI Integration:** DeepSeek API

---

## Guía de Instalación (Español)

Para configurar y ejecutar la aplicación, sigue estos pasos:

1. **Instalar dependencias:**
   Asegúrate de tener Python instalado y luego ejecuta:
   ```bash
   pip install -r requirements.txt
   ```

2. **Inicializar la base de datos:**
   Ejecuta el siguiente comando para crear la base de datos SQLite requerida (`database.db`):
   ```bash
   python init_db.py
   ```

3. **Iniciar el servidor:**
   Inicia la aplicación Flask ejecutando:
   ```bash
   python app.py
   ```
   La aplicación estará accesible a través de tu navegador web.

## Introducción a D.O.T.

D.O.T. (anteriormente Dot & Comma) es un gestor de tareas diarias centrado en las metodologías Sprint y Scrum. Está diseñado para ayudar a los usuarios a realizar un seguimiento del progreso, establecer objetivos diarios e identificar obstáculos a través de una reunión diaria (stand-up) de 15 minutos asistida por IA.

### Características
* **Stand-up de IA:** Una sesión diaria de 15 minutos con "Dot", el asistente de IA, para realizar un seguimiento del progreso y gestionar tareas.
* **Estética Retro de los 80:** El diseño visual de la aplicación se adhiere estrictamente a la estética de los monitores CRT de los años 80 (con líneas de escaneo, parpadeo de pantalla, brillo de fósforo y una pantalla de inicio estilo DOS), combinada con un estilo estructural refinado.
* **Chat Persistente:** La comunicación y notificaciones de la IA se manejan a través de una interfaz de chat persistente en la página, guardando las conversaciones en la base de datos.

### Tecnologías Utilizadas
* **Backend:** Python, Flask
* **Frontend:** HTML vainilla, CSS, JavaScript
* **Base de Datos:** SQLite (Almacenada de forma persistente en el directorio AppData del sistema)
* **Integración de IA:** API de DeepSeek
