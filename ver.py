import gspread
from google.oauth2.service_account import Credentials

SHEET_ID  = "1Ly0EsIEFkVnoaDYNjEgTzhWsSrWc1hx4_p7mdQ6zjtM"
SHEET_TAB = "Asistencia"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

values = ws.get_all_values()
print("Max columnas:", max(len(r) for r in values))
