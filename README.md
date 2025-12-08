# 🏥 Dávila Wellness Automation  
Automatización completa para matricular y registrar asistencia de colaboradores en los programas de bienestar de Clínica Dávila.  
Desarrollado en Python + Playwright + Google Sheets.

---

## 🎥 Video Demo  
> *(Aquí agregarás el link mañana, por ejemplo)*  
> 🔗 https://youtu.be/TU_VIDEO  

---

## Descripción del Proyecto

Este proyecto automatiza el proceso diario de:

1. Leer desde Google Sheets la lista de participantes según fecha.
2. Abrir automáticamente el portal de ViveBienestar.
3. Iniciar sesión como profesor.
4. Navegar por:
   - Clínica Dávila  
   - Edificio  
   - Sección  
   - Programa (Gimnasia Laboral u otros)
5. Intentar matricular participantes mediante:
   - **Plan A:** Popup rápido solo con RUT  
   - **Plan B:** Modal completo si falla el popup
6. Detectar si la persona ya estaba matriculada.
7. Marcar asistencia solo a quienes corresponda.
8. Registrar asistencias.
9. Imprimir logs claros del flujo, errores y resultados.

Este bot funciona incluso con:
- overlays molestos  
- paginación  
- formularios cambiantes  
- lentitud del sitio  
- RUT escritos de forma inconsistente

## 🧩 Arquitectura del Sistema

```mermaid
flowchart LR
    A[Google Sheets<br>Asistencia] --> B[Python Script]
    B --> C[Playwright<br>Navegador Automático]
    C --> D[ViveBienestar Web]
    D --> E[Matriculación y Asistencia]
    B --> F[Logs y Resultados]


Tecnologías Utilizadas

Python 3.10+
Playwright (automatización web)
gspread + Google API (Sheets)
dotenv (manejo seguro de credenciales)
Expresiones Regulares (RUT flexible)
Manejo de estados tolerantes a errores

Estructura del Proyecto

davila-wellness-automation/
│
├── Automatizacion_Davila.py        # Script principal
├── .gitignore                      # Exclusión de secretos
├── .env                            # Variables de entorno (no se sube)
├── credentials.json                # Credenciales Google (no se sube)
├── reports/                        # Resultados opcionales
└── README.md

Cómo Ejecutar el Proyecto
1️⃣ Instalar dependencias
pip install playwright gspread python-dotenv google-auth
playwright install

2️⃣ Crear archivo .env
URL=https://vibi.vivebienestar.cl/
EMAIL=tu_correo
PASSWORD=tu_password
SHEET_ID=XXXXXXXXXXXX
SHEET_TAB=Asistencia
FECHA_OBJ=08/12/2025
PROGRAMA=Gimnasia Laboral

3️⃣ Ejecutar
python Automatizacion_Davila.py

🔍 Lógica de Matriculación
🟢 Plan A — Popup rápido

Intenta matricular solo ingresando RUT.

Si aparece en tabla → éxito.

Plan B — Modal completo

Llena formulario completo: nombre, RUT, género.
Envia formulario estrictamente.
Reintenta si el sitio falla.

Asistencia
Marca solo a los participantes del día.
Registra asistencias al final de cada sección.

Ejemplo de Log Real
EDIFICIO C / SECCIÓN URGENCIA — 7 personas
✔ Ya estaba matriculado; asistencia marcada → Juan Soto
❌ No estaba en tabla. Intentando matricular…
   🟢 Plan A exitoso → María López
   ➕ Matriculado y asistencia marcada
💾 Registrando asistencias…
✔ Asistencias registradas.

Robustez del Bot
Maneja overlays automáticamente.
Busca botones de múltiples formas.
Permite paginación dinámica.
Reconoce RUT escritos de varias maneras.
Reintenta formularios si fallan.
Controla tiempos de carga.

Autora
Camila Álvarez
Automatización — People Analytics — Wellness Tech
Clínica Dávila / ViveBienestar

Contacto
LinkedIn: (agregar link si quieres)
Email profesional: (opcional)


---

