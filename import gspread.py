import gspread
from google.oauth2.service_account import Credentials

# === CONFIG ===
SHEET_ID  = "1Ly0EsIEFkVnoaDYNjEgTzhWsSrWc1hx4_p7mdQ6zjtM"
SHEET_TAB = "Asistencia"

# Si tu credentials.json está en la misma carpeta, déjalo así.
# Si no, pon la ruta completa:
CREDS_JSON = "credentials.json"

# Tu tabla real termina en FECHA (columna G) => 7 columnas
KEEP_COLS = 7

# MODO:
# - "clear": borra contenido desde H en adelante (recomendado)
# - "delete": elimina columnas H en adelante (deja solo A–G)
MODE = "clear"

# Seguridad: primero simula. Cuando veas que está OK, cambia a False.
DRY_RUN = False
# =================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def main():
    creds = Credentials.from_service_account_file(CREDS_JSON, scopes=SCOPES)
    gc = gspread.authorize(creds)

    ws = gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

    values = ws.get_all_values()
    max_cols = max((len(r) for r in values), default=0)
    max_rows = len(values)

    print(f"Hoja: {SHEET_TAB}")
    print(f"Filas detectadas: {max_rows}")
    print(f"Max columnas detectadas: {max_cols}")

    if max_cols <= KEEP_COLS:
        print("✅ No hay columnas extra. Nada que hacer.")
        return

    extra_start = KEEP_COLS + 1  # 8 = columna H
    extra_end = max_cols         # última columna usada

    print(f"👉 Columnas extra detectadas: {extra_start} a {extra_end} (H en adelante)")
    print(f"MODE={MODE} | DRY_RUN={DRY_RUN}")

    if MODE == "clear":
        # Borrar contenido (sin eliminar columnas)
        # Borra desde la fila 1 a la última fila detectada, columnas H..fin
        if DRY_RUN:
            print("🟡 DRY_RUN: No se borró nada. (Simulación)")
            print(f"Se borraría el rango: filas 1..{max_rows}, cols {extra_start}..{extra_end}")
        else:
            # Construye una matriz vacía para limpiar ese rango
            n_cols = extra_end - extra_start + 1
            empty_block = [[""] * n_cols for _ in range(max_rows)]
            # update usa A1 notation; usamos rango por row/col con gspread:
            ws.update(
                range_name=gspread.utils.rowcol_to_a1(1, extra_start) + ":" + gspread.utils.rowcol_to_a1(max_rows, extra_end),
                values=empty_block
            )
            print("✅ Listo: contenido extra borrado (H en adelante).")

    elif MODE == "delete":
        # Eliminar columnas completas (H..fin)
        if DRY_RUN:
            print("🟡 DRY_RUN: No se eliminó nada. (Simulación)")
            print(f"Se eliminarían columnas: {extra_start}..{extra_end} (H..fin)")
        else:
            ws.delete_columns(extra_start, extra_end)
            print("✅ Listo: columnas extra eliminadas (H en adelante).")

    else:
        raise ValueError("MODE debe ser 'clear' o 'delete'")

if __name__ == "__main__":
    main()
