# Dávila Wellness Automation  
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
5. Intentar matricular a los participantes mediante:
   - **Plan A:** Popup rápido solo con RUT  
   - **Plan B:** Llenar formulario completo del modal si el popup falla
6. Verificar si cada persona ya estaba matriculada.
7. Marcar asistencia solo para los participantes del día.
8. Registrar las asistencias.
9. Mostrar un log detallado del flujo, errores y resultados.

Este bot funciona incluso con:
- overlays molestos  
- paginación  
- formularios cambiantes  
- nombres escritos de forma inexacta  
- lentitud del sitio  

Es una automatización robusta, tolerante y estable diseñada para uso real en Clínica Dávila.

---

## Arquitectura del Sistema

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
