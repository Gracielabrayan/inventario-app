# 📦 Inventario-App (Python + Sheets API)

Este proyecto es una herramienta de automatización diseñada para gestionar inventarios de forma dinámica, utilizando **Python** como motor de lógica y **Google Sheets** como base de datos en tiempo real.

---

## 🚀 Propósito y Valor Agregado
La aplicación resuelve la problemática de la carga manual y la falta de sincronización en el control de stock. 
- **Centralización:** Todos los datos se reflejan en la nube instantáneamente.
- **Escalabilidad:** Permite que cualquier terminal con el script actualice el inventario central sin necesidad de una base de datos SQL compleja.
- **Eficiencia:** Reduce errores humanos en el ingreso de activos IT.

## 🛠️ Stack Tecnológico
- **Lenguaje:** Python 3.x
- **Integración:** Google Sheets API v4.
- **Autenticación:** Google Auth (OAuth 2.0).
- **Control de Versiones:** Git & GitHub.

## 📂 Estructura del Proyecto
- `main.py`: Punto de entrada de la aplicación y lógica de conexión.
- `requirements.txt`: Dependencias necesarias (google-api-python-client, google-auth-oauthlib).
- `assets/`: Carpeta para recursos y configuración (credenciales locales).
- `.gitignore`: Configuración de seguridad para proteger datos sensibles.
