import sys
import os

# --- PARCHE HÍBRIDO (PC Y ANDROID) ---
try:
    import wsgiref.util
    import wsgiref.simple_server
except ImportError:
    print("Aplicando parche de Android...")
    from unittest.mock import MagicMock
    m = MagicMock()
    sys.modules["wsgiref"] = m
    sys.modules["wsgiref.util"] = m
    sys.modules["wsgiref.simple_server"] = m
# ----------------------------------------

import flet as ft
import gspread
import json
import os

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

NOMBRE_LLAVE = "assets/credentials.json"
NOMBRE_DATOS = "assets/tiendas.json"

def main(page: ft.Page):
    page.title = "Inventario POS"
    page.theme_mode = "dark"
    page.padding = 20
    page.bgcolor = "#0f0f0f"
    page.scroll = "auto"

    state = {
        "sh": None, "ws": None, "datos_tiendas": {}, 
        "headers": [], "inputs": {}, "row_idx": None,
        "updating": False  # Flag para evitar loops
    }

    def mostrar_snack(texto, color="blue"):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(texto, color="white", weight="bold"), 
            bgcolor=color,
        )
        page.snack_bar.open = True
        page.update()

    # --- HEADER ---
    dd_hojas = ft.Dropdown(
        hint_text="Cargando...",
        text_size=16,
        bgcolor="#333333",
        border_radius=8,
        filled=True,
        width=400,
    )

    btn_refresh = ft.IconButton(
        icon="refresh", 
        icon_color="white", 
        bgcolor="#333333",
        on_click=lambda _: conectar()
    )

    # --- TABS ---
    txt_tienda_m = ft.TextField(
        label="Tienda", 
        prefix_icon="store",
        width=300,
        height=60,
    )
    
    txt_caja_m = ft.TextField(
        label="Caja/Dato", 
        prefix_icon="keyboard",
        width=300,
        height=60,
        on_submit=lambda e: buscar_datos(e),
    )

    dd_tienda_l = ft.Dropdown(
        label="Tienda",
        width=300,
        text_size=16,
    )
    
    dd_equipo_l = ft.Dropdown(
        label="Equipo", 
        disabled=True,
        width=300,
        text_size=16,
    )

    def actualizar_equipos(e):
        eqs = state["datos_tiendas"].get(dd_tienda_l.value, [])
        dd_equipo_l.options = [ft.dropdown.Option(str(x)) for x in eqs]
        dd_equipo_l.disabled = not bool(eqs)
        if eqs: dd_equipo_l.value = str(eqs[0])
        page.update()

    dd_tienda_l.on_change = actualizar_equipos

    def on_hoja_change(e):
        """Cambiar tab automáticamente según la hoja seleccionada"""
        if state["updating"]:
            return
        
        state["updating"] = True
        hoja = dd_hojas.value
        if hoja and ("BALANZA" in hoja.upper() or "COSTO" in hoja.upper()):
            tabs.selected_index = 1  # BALANZAS
        else:
            tabs.selected_index = 0  # POS
        state["updating"] = False
        page.update()
    
    def on_tab_change(e):
        """Cambiar hoja automáticamente según el tab seleccionado"""
        if state["updating"] or not dd_hojas.options:
            return
        
        state["updating"] = True
        
        if tabs.selected_index == 0:  # POS
            # Buscar hoja que contenga "POS" pero NO "BALANZA" ni "COSTO"
            for opt in dd_hojas.options:
                hoja = opt.key
                if "POS" in hoja.upper() and "BALANZA" not in hoja.upper() and "COSTO" not in hoja.upper():
                    dd_hojas.value = hoja
                    break
        else:  # BALANZAS
            # Buscar hoja que contenga "BALANZA" o "COSTO"
            for opt in dd_hojas.options:
                hoja = opt.key
                if "BALANZA" in hoja.upper() or "COSTO" in hoja.upper():
                    dd_hojas.value = hoja
                    break
        
        state["updating"] = False
        page.update()
    
    dd_hojas.on_change = on_hoja_change

    tabs = ft.Tabs(
        selected_index=0,
        height=220,
        on_change=on_tab_change,
        tabs=[
            ft.Tab(
                text="POS", 
                icon="keyboard",
                content=ft.Container(
                    content=ft.Column([txt_tienda_m, txt_caja_m], spacing=15),
                    padding=20,
                )
            ),
            ft.Tab(
                text="BALANZAS", 
                icon="list",
                content=ft.Container(
                    content=ft.Column([dd_tienda_l, dd_equipo_l], spacing=15),
                    padding=20,
                )
            ),
        ]
    )

    btn_buscar = ft.Container(
        content=ft.ElevatedButton(
            "BUSCAR", 
            icon="search",
            width=300,
            height=50,
            style=ft.ButtonStyle(bgcolor="#1976D2", color="white"),
            on_click=lambda e: buscar_datos(e)
        ),
        alignment=ft.alignment.center,
    )

    # --- RESULTADOS ---
    grid_res = ft.Column(spacing=15)
    
    btn_save = ft.Container(
        content=ft.ElevatedButton(
            "GUARDAR CAMBIOS", 
            icon="save", 
            disabled=True,
            width=300,
            height=50,
            style=ft.ButtonStyle(bgcolor="#388E3C", color="white"),
            on_click=lambda e: guardar(e)
        ),
        alignment=ft.alignment.center,
    )

    card_res = ft.Container(
        content=ft.Column([
            ft.Text("Editar Datos", size=20, weight="bold"),
            ft.Divider(),
            grid_res,
            ft.Container(height=20),
            btn_save
        ]),
        bgcolor="#1e1e1e", 
        padding=20, 
        border_radius=15, 
        visible=False
    )

    # --- LÓGICA ---
    def conectar():
        try:
            btn_refresh.icon = "downloading"
            page.update()
            
            json_key = NOMBRE_LLAVE
            if not os.path.exists(json_key) and os.path.exists("credentials.json"):
                json_key = "credentials.json"

            gc = gspread.service_account(filename=json_key)
            sh = gc.open_by_key(SPREADSHEET_ID)
            state["sh"] = sh
            
            hojas = [w.title for w in sh.worksheets()]
            dd_hojas.options = [ft.dropdown.Option(h) for h in hojas]
            if hojas: 
                dd_hojas.value = hojas[0]

            path_datos = NOMBRE_DATOS
            if not os.path.exists(path_datos) and os.path.exists("tiendas.json"):
                path_datos = "tiendas.json"

            if os.path.exists(path_datos):
                try:
                    with open(path_datos, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        state["datos_tiendas"] = data
                        dd_tienda_l.options = [ft.dropdown.Option(k) for k in sorted(data.keys())]
                except: 
                    pass

            btn_refresh.icon = "check"
            mostrar_snack("Conectado", "#388E3C")
        except Exception as e:
            btn_refresh.icon = "error"
            mostrar_snack(f"Error: {e}", "red")
        page.update()

    def buscar_datos(e):
        if tabs.selected_index == 0:
            tienda = txt_tienda_m.value
            dato = txt_caja_m.value.upper() if txt_caja_m.value else ""
        else:
            tienda = dd_tienda_l.value
            dato = dd_equipo_l.value if dd_equipo_l.value else ""

        if not tienda or not dd_hojas.value:
            return mostrar_snack("Faltan datos", "amber")

        try:
            ws = state["sh"].worksheet(dd_hojas.value)
            state["ws"] = ws
            vals = ws.get_all_values()
            
            headers = [str(h).upper().strip() for h in vals[0][:31]]
            state["headers"] = headers
            
            col_t = next((i for i, h in enumerate(headers) if "TIENDA" in h), 0)
            
            found = None
            for i, row in enumerate(vals[1:]):
                if len(row) > col_t and str(row[col_t]).strip() == str(tienda):
                    row_str = " ".join([str(x).upper() for x in row])
                    if not dato or str(dato).upper() in row_str:
                        found = row
                        state["row_idx"] = i + 2
                        break
            
            if found:
                grid_res.controls.clear()
                state["inputs"] = {}
                while len(found) < len(headers): 
                    found.append("")
                
                for i, h in enumerate(headers):
                    if not h: 
                        continue
                    
                    valor_actual = str(found[i])
                    is_lock = any(x in h for x in ['TIENDA', 'ID', 'CAJA'])
                    
                    if h in OPCIONES_DROPDOWN:
                        opts = [ft.dropdown.Option(opt) for opt in OPCIONES_DROPDOWN[h]]
                        campo = ft.Dropdown(
                            label=h,
                            value=valor_actual,
                            options=opts,
                            width=400,
                            text_size=16,
                        )
                    else:
                        campo = ft.TextField(
                            label=h, 
                            value=valor_actual, 
                            read_only=is_lock,
                            width=400,
                            height=60,
                            bgcolor="#1a1a1a" if is_lock else None,
                        )

                    state["inputs"][h] = campo
                    grid_res.controls.append(campo)
                
                card_res.visible = True
                btn_save.content.disabled = False
                mostrar_snack("Encontrado", "#388E3C")
            else:
                mostrar_snack("No encontrado", "red")

        except Exception as ex:
            mostrar_snack(str(ex), "red")
        page.update()

    def guardar(e):
        try:
            row = [state["inputs"].get(h, ft.TextField(value="")).value for h in state["headers"]]
            state["ws"].update(range_name=f"A{state['row_idx']}", values=[row])
            mostrar_snack("Guardado", "#388E3C")
            card_res.visible = False
            btn_save.content.disabled = True
        except Exception as ex:
            mostrar_snack(str(ex), "red")
        page.update()

    # AGREGAR TODO
    page.add(
        ft.Row([
            ft.Icon(name="inventory_2", color="#1976D2", size=30),
            ft.Text("Inventario POS", size=24, weight="bold"),
        ]),
        ft.Container(height=20),
        ft.Row([dd_hojas, btn_refresh]),
        ft.Container(height=20),
        tabs,
        ft.Container(height=20),
        btn_buscar,
        ft.Container(height=30),
        card_res,
    )
    
    conectar()

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, port=8550, host="192.168.0.17")