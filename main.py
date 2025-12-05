import sys
from unittest.mock import MagicMock

# --- PARCHE PARA ANDROID (IMPORTANTE) ---
# Engañamos a la app para que crea que existe el módulo de servidor web
# que falta en los celulares. Como no lo usamos, no pasa nada.
sys.modules["wsgiref"] = MagicMock()
sys.modules["wsgiref.simple_server"] = MagicMock()
# ----------------------------------------

import flet as ft
import gspread
import json
import os

# --- CONFIGURACIÓN ---
SPREADSHEET_ID = "1OvBfVuOusls_4PCpYn4GtBUAdX3ww0EqtXCeuMUaWBw"

# Ajuste de rutas para Android
NOMBRE_LLAVE = "assets/credentials.json"
NOMBRE_DATOS = "assets/tiendas.json"

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN VISUAL ---
    page.title = "Inventario Móvil"
    page.theme_mode = "dark"
    page.padding = 10
    page.bgcolor = "#0f0f0f"
    page.scroll = "adaptive"

    state = {
        "sh": None, "ws": None, "datos_tiendas": {}, 
        "current_headers": [], "mapa_headers": {}, 
        "inputs_editables": {}, "fila_actual": None
    }

    def mostrar_snack(texto, color="blue"):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(texto, color="white", weight="bold"), 
            bgcolor=color,
        )
        page.snack_bar.open = True
        page.update()

    # --- 2. HEADER ---
    dd_hojas = ft.Dropdown(
        hint_text="Cargando...",
        text_size=16,
        border_color="transparent",
        bgcolor="#333333",
        border_radius=8,
        filled=True,
        expand=True,
        content_padding=12,
    )

    btn_refresh = ft.IconButton(
        icon="refresh", 
        icon_color="white", 
        bgcolor="#333333",
        on_click=lambda _: conectar()
    )

    header_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(name="inventory_2", color="#1976D2", size=30),
                ft.Text("Inventario POS", size=22, weight="bold"),
            ]),
            ft.Row([dd_hojas, btn_refresh], spacing=10) 
        ]),
        padding=15,
        border_radius=15,
        bgcolor="#1e1e1e",
        margin=ft.margin.only(bottom=10)
    )

    # --- 3. INPUTS Y TABS ---
    
    # -- MANUAL --
    txt_tienda_m = ft.TextField(
        label="Tienda", prefix_icon="store", 
        col={"xs": 12, "md": 6}, border_radius=10, filled=True, bgcolor="#262626", border_width=0
    )
    txt_caja_m = ft.TextField(
        label="Caja/Dato", prefix_icon="keyboard", 
        col={"xs": 12, "md": 6}, border_radius=10, filled=True, bgcolor="#262626", border_width=0,
        on_submit=lambda e: buscar_datos(e)
    )

    # -- LISTAS --
    dd_tienda_l = ft.Dropdown(
        label="Tienda", 
        col={"xs": 12, "md": 6}, border_radius=10, filled=True, bgcolor="#262626", border_width=0
    )
    dd_equipo_l = ft.Dropdown(
        label="Equipo", 
        col={"xs": 12, "md": 6}, border_radius=10, filled=True, bgcolor="#262626", border_width=0, disabled=True
    )

    def actualizar_equipos(e):
        eqs = state["datos_tiendas"].get(dd_tienda_l.value, [])
        dd_equipo_l.options = [ft.dropdown.Option(str(x)) for x in eqs]
        dd_equipo_l.disabled = not bool(eqs)
        if eqs: dd_equipo_l.value = str(eqs[0])
        page.update()

    dd_tienda_l.on_change = actualizar_equipos

    # Tabs con altura fija para evitar error visual
    tabs_control = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        height=350, 
        tabs=[
            ft.Tab(text="Manual", icon="keyboard", content=ft.Container(content=ft.ResponsiveRow([txt_tienda_m, txt_caja_m], spacing=20), padding=20)),
            ft.Tab(text="Listas", icon="list", content=ft.Container(content=ft.ResponsiveRow([dd_tienda_l, dd_equipo_l], spacing=20), padding=20)),
        ]
    )

    btn_buscar = ft.ElevatedButton(
        "BUSCAR", icon="search", 
        style=ft.ButtonStyle(bgcolor="#1976D2", color="white", padding=15, shape=ft.RoundedRectangleBorder(radius=10)), 
        width=1000, 
        on_click=lambda e: buscar_datos(e)
    )

    # --- 4. RESULTADOS ---
    grid_res = ft.ResponsiveRow(spacing=10)
    btn_save = ft.ElevatedButton(
        "GUARDAR", icon="save", disabled=True, 
        style=ft.ButtonStyle(bgcolor="#388E3C", color="white", padding=15), 
        width=1000, 
        on_click=lambda e: guardar(e)
    )

    card_res = ft.Container(
        content=ft.Column([
            ft.Text("Editar Datos", size=18, weight="bold"),
            ft.Divider(),
            grid_res,
            ft.Container(height=10),
            btn_save
        ]),
        bgcolor="#1e1e1e", padding=20, border_radius=15, visible=False
    )

    # --- LÓGICA ---
    def conectar():
        try:
            btn_refresh.icon = "downloading"
            page.update()
            
            # Ajuste de rutas para Android
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
                dd_hojas.hint_text = "Selecciona Hoja"

            # Carga JSON local
            path_datos = NOMBRE_DATOS
            if not os.path.exists(path_datos) and os.path.exists("tiendas.json"):
                path_datos = "tiendas.json"

            if os.path.exists(path_datos):
                try:
                    with open(path_datos, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        state["datos_tiendas"] = data
                        dd_tienda_l.options = [ft.dropdown.Option(k) for k in sorted(data.keys())]
                except: pass

            btn_refresh.icon = "check"
            mostrar_snack("Conectado", "#388E3C")
        except Exception as e:
            btn_refresh.icon = "error"
            mostrar_snack(f"Error: {e}", "red")
        page.update()

    def buscar_datos(e):
        if tabs_control.selected_index == 0:
            tienda, dato = txt_tienda_m.value, txt_caja_m.value.upper()
        else:
            tienda, dato = dd_tienda_l.value, dd_equipo_l.value

        if not tienda or not dd_hojas.value:
            return mostrar_snack("Faltan datos", "amber")

        try:
            ws = state["sh"].worksheet(dd_hojas.value)
            state["ws"] = ws
            vals = ws.get_all_values()
            headers = [str(h).upper().strip() for h in vals[0][:40]]
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
                while len(found) < len(headers): found.append("")
                
                for i, h in enumerate(headers):
                    if not h: continue
                    is_lock = any(x in h for x in ['TIENDA', 'ID', 'CAJA', 'TIPO'])
                    txt = ft.TextField(label=h, value=str(found[i]), col={"xs": 12, "md": 6}, read_only=is_lock, filled=True, bgcolor="#2b2b2b" if not is_lock else "#1a1a1a")
                    state["inputs"][h] = txt
                    grid_res.controls.append(txt)
                
                card_res.visible = True
                btn_save.disabled = False
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
        except Exception as ex:
            mostrar_snack(str(ex), "red")
        page.update()

    page.add(header_container, tabs_control, btn_buscar, ft.Container(height=20), card_res)
    conectar()

if __name__ == "__main__":
    ft.app(target=main)