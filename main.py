import flet as ft
import json
import os
import sys

# --- CONFIGURACIÓN ---
SPREADSHEET_ID = "1OvBfVuOusls_4PCpYn4GtBUAdX3ww0EqtXCeuMUaWBw"

OPCIONES_DROPDOWN = {
    "TECNICO": ["Rafael Cáceres", "Alejandro Massello", "Jorge Montilla"],
    "ESTADO POS": ["POS ONLINE", "POS OFFLINE", "FUERA MLAN"],
    "CONDICION POS": ["OPERATIVA", "NO OPERATIVA", "FUERA MLAN"],
    "CPU MARCA": ["NCR", "TOSHIBA", "GIRBOY", "NO APLICA"],
    "TIPO CAJA": ["CAJA COMUN", "ECOMMERCE", "FARMACIA", "AUTOCENTER", "MAYORISTA", "SELF SCANNING", "SSCO", "AT. CLIENTE", "AUTOSERVICIO"],
    "SOFTWARE CAJA": ["NCR", "GIRBOY"],
    "PROVEEDOR TECLADO": ["TOSHIBA", "NCR", "GIRBOY", "NO APLICA"],
    "PROVEEDOR GAVETA": ["NCR", "TOSHIBA", "NO APLICA"],
    "PROVEEDOR MONITOR": ["LG", "GIRBOY", "ELO TOUCH", "ILO", "DELL", "SAMSUNG", "PHILLIPS", "NOBLEX", "HP"],
    "TIPO MONITOR": ["COMUN 19 PULG", "GIRBOY", "ELO TOUCH", "TV MONITOR ILO", "COMUN 17 PULG", "MONITOR LED 19 PULG", "193V5LSB2 / 55", "MK24X7100", "19M38A", "19M35A", "HP V190", "W1943SE"],
    "PROVEEDOR PISTOLA": ["ZEBRA", "SYMBOL", "NO APLICA", "GIRBOY", "DATALOGIC", "HONEYWELL", "WALMART"],
    "MODELO PISTOLA": ["DS2208", "LS2208", "NO APLICA", "GIRBOY", "LS4208", "GD4400", "MS5145", "QW2120", "WALMART", "QD2100"],
    "TIPO IMPRESORA": ["FISCAL", "NO FISCAL"],
    "MARCA IMPRESORA": ["EPSON", "GIRBOY"],
    "MODELO IMPRESORA": ["TM-T20II", "TM-T88IV", "TM-T88V", "GIRBOY"],
    "TIPO ESCANER": ["ESCANER BIOPTICO", "BALANZA ESCANER", "NO APLICA"],
    "PROVEEDOR ESCANER": ["HASAR", "NCR", "GIRBOY"],
    "EQUIPO": ["COSTOS", "AUTOSERVICIO"],
    "MARCA": ["METTLER TOLEDO", "SYSTEL", "RASPBERRY"],
    "SECTOR": ["VERDULERIA", "DELI", "CARNICERIA", "PESCADERIA", "FIAMBRES", "QUESOS", "LINEA DE CAJAS", "POLLOS", "BACKUP", "NO EXISTE", "ROTISERIA", "TORTAS", "REPOSTERIA"],
    "CONDICION": ["OPERATIVA", "NO OPERATIVA"],
    "MODELO": ["COSTOS", "HIBRIDA", "GIRBOY"]
}

# Rutas relativas para Android
NOMBRE_LLAVE = "assets/credentials.json"
NOMBRE_DATOS = "assets/tiendas.json"
NOMBRE_DATOS_POS = "assets/tiendas_pos.json"

def main(page: ft.Page):
    # Configuración básica visual antes de cargar nada pesado
    page.title = "Cargando..."
    page.theme_mode = "dark"
    page.bgcolor = "#0f0f0f"
    page.padding = 20
    page.scroll = "auto"

    # --- TEXTO DE DEBUG (Vital para ver errores en el celular) ---
    txt_debug = ft.Text("Iniciando sistema...", color="yellow", size=16)
    page.add(txt_debug)
    page.update()

    # --- CARGA PROTEGIDA DE LIBRERÍAS ---
    try:
        txt_debug.value = "Cargando librería gspread..."
        page.update()
        
        # IMPORTAMOS AQUÍ, NO ARRIBA. 
        # Si falla, saltamos al except sin romper la pantalla.
        import gspread 
        
        txt_debug.value = "Librerías cargadas. Iniciando interfaz..."
        page.update()
    except Exception as e_import:
        page.clean()
        page.add(
            ft.Column([
                ft.Icon(ft.icons.BROKEN_IMAGE, color="red", size=60),
                ft.Text("ERROR DE LIBRERÍA", color="red", size=30, weight="bold"),
                ft.Text("Falta una librería en requirements.txt", size=20, weight="bold"),
                ft.Divider(),
                ft.Text(f"Detalle técnico:\n{e_import}", size=16, color="white"),
            ])
        )
        return # Detenemos la ejecución aquí

    # --- ESTADO DE LA APP ---
    state = {
        "sh": None, "ws": None, 
        "datos_tiendas": {}, 
        "datos_pos": {},     
        "headers": [], "inputs": {}, "row_idx": None,
        "updating": False 
    }

    def mostrar_snack(texto, color="blue"):
        page.snack_bar = ft.SnackBar(content=ft.Text(texto, color="white", weight="bold"), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # --- DEFINICIÓN DE CONTROLES (Tu código original) ---
    dd_hojas = ft.Dropdown(hint_text="Cargando hojas...", text_size=16, bgcolor="#333333", border_radius=8, filled=True, width=400)
    btn_refresh = ft.IconButton(icon="refresh", icon_color="white", bgcolor="#333333", on_click=lambda _: conectar())

    # Controles POS
    dd_tienda_pos = ft.Dropdown(label="Tienda (POS)", width=300, text_size=16, icon="store")
    dd_caja_pos = ft.Dropdown(label="Caja #", width=300, text_size=16, disabled=True, icon="point_of_sale")
    
    # Controles Balanzas
    dd_tienda_l = ft.Dropdown(label="Tienda (Balanza)", width=300, text_size=16)
    dd_equipo_l = ft.Dropdown(label="Equipo / IP", disabled=True, width=300, text_size=16)

    def actualizar_cajas_pos(e):
        tienda_sel = dd_tienda_pos.value
        cajas = state["datos_pos"].get(tienda_sel, [])
        if cajas: cajas.sort()
        dd_caja_pos.options = [ft.dropdown.Option(str(x)) for x in cajas]
        dd_caja_pos.disabled = not bool(cajas)
        dd_caja_pos.value = None
        page.update()

    def actualizar_equipos(e):
        eqs = state["datos_tiendas"].get(dd_tienda_l.value, [])
        dd_equipo_l.options = [ft.dropdown.Option(str(x)) for x in eqs]
        dd_equipo_l.disabled = not bool(eqs)
        if eqs: dd_equipo_l.value = str(eqs[0])
        page.update()

    dd_tienda_pos.on_change = actualizar_cajas_pos
    dd_tienda_l.on_change = actualizar_equipos

    def on_hoja_change(e):
        if state["updating"]: return
        state["updating"] = True
        hoja = dd_hojas.value
        if hoja and ("BALANZA" in hoja.upper() or "COSTO" in hoja.upper()):
            tabs.selected_index = 1
        else:
            tabs.selected_index = 0
        state["updating"] = False
        page.update()

    def on_tab_change(e):
        if state["updating"] or not dd_hojas.options: return
        state["updating"] = True
        if tabs.selected_index == 0:
            for opt in dd_hojas.options:
                if "POS" in opt.key.upper() and "BALANZA" not in opt.key.upper() and "COSTO" not in opt.key.upper():
                    dd_hojas.value = opt.key; break
        else:
            for opt in dd_hojas.options:
                if "BALANZA" in opt.key.upper() or "COSTO" in opt.key.upper():
                    dd_hojas.value = opt.key; break
        state["updating"] = False
        page.update()

    dd_hojas.on_change = on_hoja_change
    tabs = ft.Tabs(
        selected_index=0, height=220, on_change=on_tab_change,
        tabs=[
            ft.Tab(text="POS", icon="keyboard", content=ft.Container(content=ft.Column([dd_tienda_pos, dd_caja_pos], spacing=15), padding=20)),
            ft.Tab(text="BALANZAS", icon="list", content=ft.Container(content=ft.Column([dd_tienda_l, dd_equipo_l], spacing=15), padding=20)),
        ]
    )

    btn_buscar = ft.Container(content=ft.ElevatedButton("BUSCAR", icon="search", width=300, height=50, style=ft.ButtonStyle(bgcolor="#1976D2", color="white"), on_click=lambda e: buscar_datos(e)), alignment=ft.alignment.center)
    
    grid_res = ft.Column(spacing=15)
    btn_save = ft.Container(content=ft.ElevatedButton("GUARDAR CAMBIOS", icon="save", disabled=True, width=300, height=50, style=ft.ButtonStyle(bgcolor="#388E3C", color="white"), on_click=lambda e: guardar(e)), alignment=ft.alignment.center)
    card_res = ft.Container(content=ft.Column([ft.Text("Editar Datos", size=20, weight="bold"), ft.Divider(), grid_res, ft.Container(height=20), btn_save]), bgcolor="#1e1e1e", padding=20, border_radius=15, visible=False)

    # --- LÓGICA DE CONEXIÓN ---
    def conectar():
        txt_debug.value = "Conectando..."
        page.update()
        try:
            btn_refresh.icon = "downloading"
            page.update()
            
            # Chequeo de seguridad de archivos
            if not os.path.exists(NOMBRE_LLAVE):
                raise FileNotFoundError(f"Falta archivo: {NOMBRE_LLAVE}")
            
            gc = gspread.service_account(filename=NOMBRE_LLAVE)
            sh = gc.open_by_key(SPREADSHEET_ID)
            state["sh"] = sh
            
            hojas = [w.title for w in sh.worksheets()]
            dd_hojas.options = [ft.dropdown.Option(h) for h in hojas]
            if hojas: dd_hojas.value = hojas[0]

            # Cargar JSONs
            for ruta, destino_state, dd_obj in [(NOMBRE_DATOS, "datos_tiendas", dd_tienda_l), (NOMBRE_DATOS_POS, "datos_pos", dd_tienda_pos)]:
                if os.path.exists(ruta):
                    with open(ruta, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        state[destino_state] = data
                        dd_obj.options = [ft.dropdown.Option(k) for k in sorted(data.keys())]
            
            btn_refresh.icon = "check"
            txt_debug.value = "" # Borramos el texto de debug si todo sale bien
            mostrar_snack("Conectado", "#388E3C")
            
        except Exception as e:
            btn_refresh.icon = "error"
            txt_debug.value = f"ERROR AL CONECTAR: {str(e)}"
            txt_debug.color = "red"
            mostrar_snack(f"Error: {e}", "red")
        page.update()

    # Función auxiliar para comparar 015 == 15
    def es_coincidencia(valor_celda, valor_buscado):
        s_celda, s_buscado = str(valor_celda).strip().upper(), str(valor_buscado).strip().upper()
        if not s_buscado: return True
        if s_celda == s_buscado: return True
        if s_celda.isdigit() and s_buscado.isdigit(): return int(s_celda) == int(s_buscado)
        return False

    def buscar_datos(e):
        try:
            if tabs.selected_index == 0:
                tienda, dato = str(dd_tienda_pos.value).strip(), str(dd_caja_pos.value).strip() if dd_caja_pos.value else ""
            else:
                tienda, dato = str(dd_tienda_l.value).strip(), str(dd_equipo_l.value).strip() if dd_equipo_l.value else ""

            if not tienda or not dd_hojas.value: return mostrar_snack("Faltan datos", "amber")

            ws = state["sh"].worksheet(dd_hojas.value)
            state["ws"] = ws
            vals = ws.get_all_values()
            if not vals: return mostrar_snack("Hoja vacía", "red")
            
            headers = [str(h).upper().strip() for h in vals[0][:35]]
            state["headers"] = headers
            found = None
            
            # TU LÓGICA DE BÚSQUEDA FUERZA BRUTA
            for i, row in enumerate(vals[1:]):
                tienda_en_fila = False
                for celda in row:
                    if es_coincidencia(celda, tienda):
                        tienda_en_fila = True; break
                
                if tienda_en_fila:
                    match = False
                    if not dato: match = True
                    else:
                        for celda in row:
                            if es_coincidencia(celda, dato):
                                match = True; break
                    if match:
                        found = row; state["row_idx"] = i + 2; break
            
            if found:
                grid_res.controls.clear()
                state["inputs"] = {}
                while len(found) < len(headers): found.append("")
                for i, h in enumerate(headers):
                    if not h: continue
                    val = str(found[i])
                    is_lock = any(x in h for x in ['TIENDA', 'ID', 'CAJA', 'SUCURSAL', 'POS'])
                    if h in OPCIONES_DROPDOWN:
                        opts = [ft.dropdown.Option(o) for o in OPCIONES_DROPDOWN[h]]
                        if val and val not in OPCIONES_DROPDOWN[h]: opts.append(ft.dropdown.Option(val))
                        campo = ft.Dropdown(label=h, value=val, options=opts, width=400, text_size=16)
                    else:
                        campo = ft.TextField(label=h, value=val, read_only=is_lock, width=400, height=60, bgcolor="#1a1a1a" if is_lock else None)
                    state["inputs"][h] = campo; grid_res.controls.append(campo)
                card_res.visible = True; btn_save.content.disabled = False; mostrar_snack("Encontrado", "#388E3C")
            else: mostrar_snack(f"No encontrado: {tienda} - {dato}", "red")
        except Exception as ex: mostrar_snack(str(ex), "red")
        page.update()

    def guardar(e):
        try:
            row = [state["inputs"].get(h, ft.TextField(value="")).value for h in state["headers"]]
            state["ws"].update(range_name=f"A{state['row_idx']}", values=[row])
            mostrar_snack("Guardado", "#388E3C"); card_res.visible = False; btn_save.content.disabled = True
        except Exception as ex: mostrar_snack(str(ex), "red")
        page.update()

    # --- ARMAR PAGINA ---
    page.clean()
    page.add(
        ft.Row([ft.Icon(name="inventory_2", color="#1976D2", size=30), ft.Text("Inventario POS", size=24, weight="bold")]),
        ft.Container(height=20),
        ft.Row([dd_hojas, btn_refresh]),
        txt_debug, # El texto que nos dirá si algo falla
        ft.Container(height=20),
        tabs,
        ft.Container(height=20),
        btn_buscar,
        ft.Container(height=30),
        card_res,
    )
    
    conectar()

if __name__ == "__main__":
    ft.app(target=main)