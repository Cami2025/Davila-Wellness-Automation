# Automatizacion_Davila.py
# -*- coding: utf-8 -*-

import os, re, datetime as dt
from collections import defaultdict
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# ===================== 
# 0) .env y constantes
# =====================
load_dotenv()
URL        = os.getenv("URL", "https://vibi.vivebienestar.cl/")
EMAIL      = os.getenv("EMAIL", "")
PASSWORD   = os.getenv("PASSWORD", "")
SHEET_ID   = os.getenv("SHEET_ID", "")
SHEET_TAB  = os.getenv("SHEET_TAB", "Asistencia")
RAW_FECHA  = (os.getenv("FECHA_OBJ") or os.getenv("FECHA_OBJETIVO") or "").strip()
PROGRAMA   = os.getenv("PROGRAMA", "Gimnasia Laboral")

def log(s):
    print(s, flush=True)

def regex_exact(t):
    return re.compile(rf"^\s*{re.escape(t)}\s*$", re.I)

def parse_fecha(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y","%-d/%-m/%Y","%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except:
            pass
    try:
        return dt.date.fromisoformat(s)
    except:
        return dt.date.today()

FECHA_OBJ = parse_fecha(RAW_FECHA)

# ==========================
# Utils: overlays y navegación
# ==========================
def clear_overlays(page):
    try:
        for txt in ["Cerrar", "OK", "Aceptar", "Entendido", "Hecho", "Continuar", "Sí"]:
            btn = page.get_by_role("button", name=re.compile(rf"^{txt}$", re.I))
            if btn.count():
                try:
                    btn.first.click()
                except:
                    try: btn.first.click(force=True)
                    except: pass
        for sel in [".mfp-close",".swal2-close",".modal-header .close","[aria-label='Close']"]:
            loc = page.locator(sel)
            if loc.count():
                try:
                    loc.first.click()
                except:
                    try: loc.first.click(force=True)
                    except: pass
        try:
            page.keyboard.press("Escape")
        except:
            pass
    except:
        pass

def volver_a_inicio(page):
    """Vuelve a la pantalla principal (Profesor / Clínica Dávila)."""
    clear_overlays(page)
    ini = page.get_by_role("link", name=re.compile(r"Inicio", re.I))
    if ini.count():
        try:
            ini.first.click()
        except:
            ini.first.click(force=True)
        page.wait_for_load_state("networkidle")
    else:
        page.goto(URL, wait_until="domcontentloaded")
    page.get_by_text(re.compile(r"Profesor\s*:\s*", re.I)).first.wait_for(timeout=10000)

# ==========================
# 1) Utilidades de RUT/tabla
# ==========================
def _normaliza_rut(rut: str) -> str:
    rut = str(rut).strip().upper().replace(".", "").replace(" ", "")
    if "-" not in rut and len(rut) >= 2:
        rut = rut[:-1] + "-" + rut[-1]
    return rut

def _rut_regex(rut: str):
    base = _normaliza_rut(rut)
    if "-" not in base:
        return re.compile(re.escape(base), re.I)
    num, dv = base.split("-")
    num_pat = r"\.?".join(list(num))
    dv_pat  = r"[Kk]" if dv.upper()=="K" else re.escape(dv)
    return re.compile(rf"(?<!\d){num_pat}-?{dv_pat}(?!\d)", re.I)

def _fila_por_rut(page, rut_pat):
    # tabla principal de participantes
    return page.locator("#tabla_participante_front tr").filter(has_text=rut_pat)

def _tiene_paginacion(page):
    return page.locator(".pagination, nav[aria-label*='pagination'], ul.pagination, [rel='next']").count() > 0

def _siguiente_pagina(page) -> bool:
    clear_overlays(page)
    cand = [
        page.get_by_role("link", name=re.compile(r"Siguiente|Next|›|»", re.I)),
        page.locator("[rel='next']"),
        page.locator("a:has-text('›'), a:has-text('»'), a:has-text('Siguiente'), a:has-text('Next')"),
        page.locator("button:has-text('›'), button:has-text('»'), button:has-text('Siguiente'), button:has-text('Next')"),
    ]
    for loc in cand:
        if loc.count():
            try:
                loc.last.click()
                page.wait_for_timeout(320)
                return True
            except:
                try:
                    loc.last.click(force=True)
                    page.wait_for_timeout(320)
                    return True
                except:
                    pass
    return False

def verificar_en_tabla(page, rut, max_paginas=8) -> bool:
    """Solo booleano: ¿aparece el RUT en alguna página?"""
    return buscar_fila_por_rut(page, rut, max_paginas) is not None

def buscar_fila_por_rut(page, rut, max_paginas=8):
    """Devuelve la fila (<tr>) del participante con ese RUT, o None."""
    pat = _rut_regex(rut)
    fila = _fila_por_rut(page, pat)
    if fila.count():
        return fila.first
    if not _tiene_paginacion(page):
        return None
    for _ in range(max_paginas):
        if not _siguiente_pagina(page):
            break
        fila = _fila_por_rut(page, pat)
        if fila.count():
            return fila.first
    return None

def marcar_asistencia_por_rut(page, rut, max_paginas=8) -> bool:
    """Marca el checkbox de asistencia SOLO del RUT indicado."""
    fila = buscar_fila_por_rut(page, rut, max_paginas=max_paginas)
    if not fila:
        return False
    chk = fila.locator("input[type='checkbox'][name='asistencia[]']")
    if not chk.count():
        return False
    try:
        chk.first.check(timeout=2000)
        return True
    except:
        try:
            chk.first.check(force=True, timeout=2000)
            return True
        except:
            return False

# ==========================
# 2) Lectura desde la Sheet
# ==========================
def fecha_iso_de_sheet(v):
    txt = str(v).strip()
    for fmt in ("%d/%m/%Y","%-d/%-m/%Y","%m/%d/%Y"):
        try:
            return dt.datetime.strptime(txt, fmt).date().isoformat()
        except:
            pass
    try:
        return dt.date.fromisoformat(txt).isoformat()
    except:
        return ""

def leer_personas_por_fecha():
    """Devuelve dict agrupado: {(EDIFICIO, SECCION): [ {APELLIDO,NOMBRE,RUT,GENERO} ]}"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    gc = gspread.authorize(creds)

    ws = gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)
    rows = ws.get_all_records()

    objetivo_iso = FECHA_OBJ.isoformat()
    grupos = defaultdict(list)
    for r in rows:
        if fecha_iso_de_sheet(r.get("FECHA","")) != objetivo_iso:
            continue
        apellido = str(r.get("APELLIDO","")).strip()
        nombre   = str(r.get("NOMBRE","")).strip()
        rut      = _normaliza_rut(r.get("RUT",""))
        edificio = str(r.get("EDIFICIO","")).strip()
        seccion  = str(r.get("SECCION","")).strip()
        genero   = str(r.get("GENERO", r.get("GÉNERO","Femenino"))).strip() or "Femenino"
        if not (apellido and nombre and rut and edificio and seccion):
            continue
        grupos[(edificio, seccion)].append({
            "NOMBRE_COMPLETO": f"{apellido} {nombre}",
            "APELLIDO": apellido,
            "NOMBRE": nombre,
            "RUT": rut,
            "GENERO": genero
        })
    return grupos

# ==========================
# 3) Navegación con Playwright
# ==========================
def abrir_clinica(page, titulo="Clínica Dávila"):
    """Abre el acordeón 'Clínica Dávila' de forma tolerante."""
    log("⏩ Abriendo panel de Clínica…")
    try:
        page.get_by_text(re.compile(r"EDIFICIO\s+[A-Z]", re.I)).first.wait_for(timeout=800)
        log("✅ Panel 'Clínica Dávila' ya abierto.")
        return True
    except:
        pass

    clear_overlays(page)
    page.wait_for_load_state("domcontentloaded")

    candidatos = [
        page.get_by_text(re.compile(r"^\s*Cl[ií]nica\s+D[aá]vila\s*$", re.I)),
        page.get_by_text(re.compile(r"Cl[ií]nica\s+D[aá]vila", re.I)),
        page.locator(
            "xpath=//*[contains("
            "translate(normalize-space(.),'ÁÉÍÓÚáéíóú','AEIOUaeiou'),"
            "'Clinica Davila'"
            ")]"
        ),
    ]

    for loc in candidatos:
        if loc.count():
            try:
                try:
                    loc.first.scroll_into_view_if_needed(timeout=1200)
                except:
                    pass
                try:
                    loc.first.click(timeout=1200)
                except:
                    loc.first.click(force=True, timeout=1200)
                page.wait_for_timeout(300)
                page.get_by_text(re.compile(r"EDIFICIO\s+[A-Z]", re.I)).first.wait_for(timeout=1500)
                log("✅ Panel abierto.")
                return True
            except:
                continue

    log("⚠ No pude abrir el panel 'Clínica Dávila'.")
    return False

def ir_a_edificio(page, letra):
    if not abrir_clinica(page):
        raise RuntimeError("No se pudo abrir 'Clínica Dávila'")
    clear_overlays(page)
    link = page.get_by_text(regex_exact(f"EDIFICIO {letra}"))
    if not link.count():
        link = page.locator("a").filter(has_text=re.compile(rf"EDIFICIO\s+{re.escape(letra)}", re.I))
    link.first.scroll_into_view_if_needed()
    try:
        link.first.click()
    except:
        link.first.click(force=True)
    page.get_by_text(re.compile(r"Programas|Gimnasia|Volver|Sección|Grupo", re.I)).first.wait_for(timeout=10000)

def ir_a_seccion(page, seccion):
    objetivo = regex_exact(seccion)
    link = page.get_by_role("link", name=objetivo)
    if not link.count():
        link = page.locator("a").filter(has_text=objetivo)
    link.first.scroll_into_view_if_needed()
    try:
        link.first.click()
    except:
        link.first.click(force=True)

def ir_a_programa(page, preferido=PROGRAMA):
    prog = page.get_by_role("link", name=regex_exact(preferido))
    if not prog.count():
        prog = page.locator("a").filter(has_text=re.compile(re.escape(preferido), re.I))
    if prog.count():
        prog.first.scroll_into_view_if_needed()
        try:
            prog.first.click()
        except:
            prog.first.click(force=True)
    page.get_by_text(
        re.compile(r"Buscar por Nombre|Registrar Asistencias|Agregar Participante|Matricular Participante", re.I)
    ).first.wait_for(timeout=12000)

def abrir_modal_matricula(page):
    boton = page.get_by_role("button", name=re.compile(r"^\s*Matricular\s+Participante\s*$", re.I))
    if not boton.count():
        boton = page.locator("button,a").filter(has_text=re.compile(r"Matricular\s+Participante", re.I))
    if not boton.count():
        log("⛔ No encontré botón Matricular Participante.")
        return False
    b = boton.first
    b.scroll_into_view_if_needed()
    try:
        b.click()
    except:
        b.click(force=True)
    scope = page.get_by_role("dialog")
    if not scope.count():
        scope = page
    scope.locator("form input, form select").first.wait_for(timeout=8000)
    return True

# =========================================
# 4) Guardar/Confirmaciones (estricto)
# =========================================
def _submit_form_estricto(form_locator):
    f = form_locator.first
    subs = f.locator("input[type='submit'], button[type='submit']")
    if subs.count():
        try:
            subs.first.scroll_into_view_if_needed()
        except Exception:
            pass
        try:
            subs.first.click(timeout=1500)
            return True
        except Exception:
            try:
                subs.first.click(force=True, timeout=1500)
                return True
            except Exception:
                pass
    try:
        f.evaluate("""
            (el) => {
              if (el.reportValidity && !el.reportValidity()) return;
              el.dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
              if (typeof el.submit === 'function') el.submit();
            }
        """)
        return True
    except Exception:
        return False

def _dismiss_confirmations(page):
    try:
        ok = page.get_by_role(
            "button",
            name=re.compile(r"^(OK|Aceptar|Entendido|Sí|Continuar)$", re.I),
        )
        if ok.count():
            try:
                ok.first.click()
            except Exception:
                ok.first.click(force=True)
            page.wait_for_timeout(300)
    except Exception:
        pass

# ==========================
# 5A) PLAN A: popup rápido solo con RUT
# ==========================
def agregar_participante_rapido(page, rut: str) -> bool:
    """Plan A: usa el popup rápido de matrícula por RUT (si existe)."""
    rut_norm = _normaliza_rut(rut)
    log(f"   🔹 Plan A: intentando popup rápido con RUT {rut_norm}…")

    try:
        clear_overlays(page)

        boton = page.locator("button.matricular_participante, button#matricular_participante")
        if not boton.count():
            boton = page.get_by_role(
                "button",
                name=re.compile(r"Agregar\s+Participante|Matricular\s+Participante", re.I),
            )
        if not boton.count():
            log("      ⛔ No encontré botón de popup rápido.")
            return False

        boton.first.scroll_into_view_if_needed()
        try:
            boton.first.click()
        except:
            boton.first.click(force=True)

        campo = page.locator("#rut_parti_matri")
        if not campo.count():
            campo = page.locator("#rut_parti, input[name*='rut'], input[id*='rut']")
        if not campo.count():
            log("      ⚠ No encontré input de RUT en el popup.")
            return False

        campo.first.wait_for(timeout=4000)
        campo.first.fill(rut_norm)

        try:
            campo.first.dispatch_event("keyup")
            campo.first.dispatch_event("input")
            campo.first.dispatch_event("change")
        except Exception:
            pass

        btn_env = page.locator("#enviar_matricula")
        if not btn_env.count():
            btn_env = page.locator(
                "button:has-text('Agregar'), button:has-text('Matricular'), button:has-text('Guardar')"
            )

        if not btn_env.count():
            log("      ⚠ No encontré botón 'Agregar/Matricular' en el popup.")
            return False

        try:
            btn_env.first.click()
        except:
            btn_env.first.click(force=True)

        page.wait_for_timeout(2500)
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except:
            pass

        _dismiss_confirmations(page)

        if verificar_en_tabla(page, rut_norm, max_paginas=4):
            log("      🟢 Plan A exitoso (popup).")
            return True
        else:
            log("      ⚠ Plan A no encontró el RUT después del intento.")
            return False

    except Exception as e:
        log(f"      ⛔ Error en Plan A: {e}")
        return False

# ==========================
# 5B) PLAN B: Llenar modal y guardar
# ==========================
def matricular_en_modal(page, nombre: str, rut: str, genero: str = "Femenino") -> bool:
    scope = page.get_by_role("dialog")
    scope = scope.first if scope.count() else page
    form = scope.locator("form").first
    form.wait_for(timeout=8000)

    # Nombre
    ok_nom = False
    for pat in [r"^Nombre\b", r"^Nombre Completo\b", r"Nombres y Apellidos"]:
        ll = form.get_by_label(re.compile(pat, re.I))
        if ll.count():
            ll.first.fill(nombre)
            ok_nom = True
            break
    if not ok_nom:
        pl = form.get_by_placeholder(re.compile("Nombre", re.I))
        if pl.count():
            pl.first.fill(nombre)
            ok_nom = True
    if not ok_nom:
        inp = form.locator("input[name*='nombre'], input[id*='nombre'], #nombre_parti")
        if inp.count():
            inp.first.fill(nombre)
            ok_nom = True

    # RUT
    rut = _normaliza_rut(rut)
    ok_rut = False
    direct_rut = form.locator("#rut_parti")
    if direct_rut.count():
        direct_rut.first.fill(rut)
        try:
            direct_rut.first.dispatch_event("keyup")
            direct_rut.first.dispatch_event("input")
            direct_rut.first.dispatch_event("change")
        except Exception:
            pass
        ok_rut = True
    if not ok_rut:
        for pat in [r"^Rut\b", r"^RUT\b", r"^RUN\b", r"Documento"]:
            ll = form.get_by_label(re.compile(pat, re.I))
            if ll.count():
                ll.first.fill(rut)
                ok_rut = True
                break
        if not ok_rut:
            pl = form.get_by_placeholder(re.compile("Rut|RUT|RUN|Documento", re.I))
            if pl.count():
                pl.first.fill(rut)
                ok_rut = True
        if not ok_rut:
            inp = form.locator(
                "input[name*='rut'], input[id*='rut'], input[name*='run'], input[id*='run']"
            )
            if inp.count():
                inp.first.fill(rut)
                ok_rut = True

    # Género (si existe)
    sel = form.locator(
        "#genero, label:has-text('Género') ~ select, select[name*='genero'], select[id*='genero']"
    )
    if sel.count():
        try:
            sel.first.select_option(label=re.compile(re.escape(genero or "Femenino"), re.I))
        except Exception:
            pass

    if not _submit_form_estricto(form):
        log("⚠ No encontré cómo enviar el formulario (ningún submit dentro del modal).")
        return False

    page.wait_for_timeout(800)
    _dismiss_confirmations(page)

    if verificar_en_tabla(page, rut, max_paginas=8):
        return True

    _submit_form_estricto(form)
    page.wait_for_timeout(800)
    return verificar_en_tabla(page, rut, max_paginas=8)

# ==========================
# 5C) Registrar asistencias
# ==========================
def registrar_asistencias(page):
    log("💾 Registrando asistencias…")
    boton = page.locator("#enviar_asistencia, button.enviar_asistencia")
    if not boton.count():
        log("   ⛔ No encontré el botón 'Registrar Asistencias'")
        return False
    try:
        boton.first.click()
    except:
        boton.first.click(force=True)
    page.wait_for_timeout(1500)
    _dismiss_confirmations(page)
    log("   ✔ Asistencias registradas.")
    return True

# ==========================
# 6) Orquestador (Plan A + Plan B + asistencia)
# ==========================
def main():
    grupos = leer_personas_por_fecha()
    total = sum(len(v) for v in grupos.values())
    log(f"📅 FECHA {FECHA_OBJ.isoformat()} — Total personas: {total}")
    if total == 0:
        log("No hay personas para esa fecha.")
        return

    with sync_playwright() as pw:
        # ✅ Cambio: en tu PC por defecto abre ventana; en Actions puedes forzar HEADLESS=1
        HEADLESS = os.getenv("HEADLESS", "0").strip() != "0"
        browser = pw.chromium.launch(headless=HEADLESS)

        context = browser.new_context(viewport={"width": 1366, "height": 840})
        page = context.new_page()

        # Login
        log("🔑 Iniciando sesión…")
        page.goto(URL, wait_until="domcontentloaded")
        try:
            page.get_by_label(re.compile("usuario|correo|email", re.I)).first.fill(EMAIL)
        except Exception:
            page.locator("input[type='email'], input[name*='user'], input[name*='email']").first.fill(EMAIL)
        page.locator("input[type='password']").first.fill(PASSWORD)
        page.locator("input[type='submit'], button[type='submit']").first.click()
        page.wait_for_load_state("networkidle")

        # Por cada (EDIFICIO, SECCION)
        for (edificio, seccion), personas in grupos.items():
            log(f"\n➡️ EDIFICIO {edificio} / SECCIÓN {seccion} — {len(personas)} personas")
            try:
                if not abrir_clinica(page):
                    log("   ⛔ No pude abrir 'Clínica Dávila'. Salto grupo.")
                    continue
                ir_a_edificio(page, edificio)
                ir_a_seccion(page, seccion)
                ir_a_programa(page, PROGRAMA)

                # Procesar personas: matricular si falta y marcar asistencia SOLO a ellas
                for p in personas:
                    nombre = p["NOMBRE_COMPLETO"]
                    rut    = p["RUT"]
                    genero = p["GENERO"] or "Femenino"

                    # 1) ¿Ya existe en la tabla?
                    fila = buscar_fila_por_rut(page, rut, max_paginas=8)

                    if fila:
                        # Ya estaba matriculado → solo marcar asistencia
                        if marcar_asistencia_por_rut(page, rut, max_paginas=8):
                            log(f"   ✔ Ya estaba matriculado; asistencia marcada → {nombre} ({rut})")
                        else:
                            log(f"   ⚠ Ya estaba registrado {nombre} ({rut})")
                        continue

                    # 2) No existe → Matricular (Plan A, luego Plan B)
                    log(f"   ❌ No estaba en tabla. Intentando matricular → {nombre} ({rut})")

                    ok_rapido = agregar_participante_rapido(page, rut)
                    if ok_rapido:
                        log(f"   ✅ Plan A OK → {nombre} ({rut})")
                    else:
                        log("   🔁 Plan A falló. Probando Plan B (modal)…")
                        if not abrir_modal_matricula(page):
                            log("   ⛔ No pude abrir el modal de matrícula (saltando persona).")
                            continue
                        ok_modal = matricular_en_modal(page, nombre, rut, genero)
                        if ok_modal:
                            log(f"   ✅ Plan B OK → {nombre} ({rut})")
                        else:
                            log(f"   ⚠ No se pudo matricular ni con Plan A ni con Plan B → {nombre} ({rut})")
                            continue  # no hay matrícula → no se puede marcar asistencia

                    # 3) Después de matricular, marcar asistencia de ese RUT
                    if marcar_asistencia_por_rut(page, rut, max_paginas=8):
                        log(f"   ➕ Matriculado y asistencia marcada → {nombre} ({rut})")
                    else:
                        log(f"   ➕ Matriculado, pero no pude marcar asistencia → {nombre} ({rut})")

                # 4) Registrar todas las asistencias marcadas del grupo
                registrar_asistencias(page)

            except Exception as e:
                log(f"❌ Error en {edificio}/{seccion}: {e}")

            # Volver a Inicio para el siguiente grupo
            try:
                volver_a_inicio(page)
            except Exception as e:
                log(f"↩️ No pude volver a Inicio automáticamente: {e}. Reintentando por URL…")
                try:
                    page.goto(URL, wait_until="domcontentloaded")
                    page.get_by_text(re.compile(r"Profesor\s*:\s*", re.I)).first.wait_for(timeout=8000)
                except Exception:
                    pass

        log("\n🏁 Listo (Plan A + Plan B + asistencia).")

if __name__ == "__main__":
    main()
