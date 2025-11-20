import flet as ft
import sqlite3
import shutil
import os
import datetime

# Aseguramos que exista carpeta para guardar las imagenes
if not os.path.exists("assets"):
    os.makedirs("assets")

def main(page: ft.Page):
    page.title = "Cocina Smart 2.0"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 380
    page.window_height = 750
    page.padding = 0 
    
    # Variable para guardar temporalmente la ruta de la foto seleccionada
    imagen_seleccionada = ft.Ref[str]() 
    
    # --- BASE DE DATOS ---
    def inicializar_db():
        conn = sqlite3.connect("cocina.db")
        cursor = conn.cursor()
        # Tabla productos con columna de imagen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cantidad REAL DEFAULT 0,
                unidad TEXT DEFAULT 'unidad',
                imagen TEXT DEFAULT NULL
            )
        ''')
        # Tabla historial para saber qué se comió
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_producto INTEGER,
                cantidad_usada REAL,
                tipo_comida TEXT,
                fecha TEXT
            )
        ''')
        conn.commit()
        conn.close()

    inicializar_db()

    # --- FUNCIONES DE LOGICA ---
    def obtener_productos():
        conn = sqlite3.connect("cocina.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos")
        items = cursor.fetchall()
        conn.close()
        return items

    def guardar_producto(nombre, cantidad, unidad, ruta_img):
        # Si hay imagen, la copiamos a la carpeta assets
        ruta_final = None
        if ruta_img:
            nombre_archivo = os.path.basename(ruta_img)
            destino = os.path.join("assets", nombre_archivo)
            try:
                shutil.copy(ruta_img, destino)
                ruta_final = destino
            except:
                ruta_final = None # Si falla, guardamos sin imagen

        conn = sqlite3.connect("cocina.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, cantidad, unidad, imagen) VALUES (?, ?, ?, ?)", 
                       (nombre, cantidad, unidad, ruta_final))
        conn.commit()
        conn.close()

    def consumir_producto(id_prod, cantidad_usada, tipo_comida, stock_actual):
        conn = sqlite3.connect("cocina.db")
        cursor = conn.cursor()
        
        # 1. Descontar del inventario
        nuevo_stock = max(0, stock_actual - cantidad_usada)
        cursor.execute("UPDATE productos SET cantidad = ? WHERE id = ?", (nuevo_stock, id_prod))
        
        # 2. Guardar en historial
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO historial (id_producto, cantidad_usada, tipo_comida, fecha) VALUES (?, ?, ?, ?)",
                       (id_prod, cantidad_usada, tipo_comida, fecha))
        
        conn.commit()
        conn.close()
        
        page.snack_bar = ft.SnackBar(ft.Text(f"¡Descontado de {tipo_comida}!"))
        page.snack_bar.open = True
        page.update()
        # Recargar la vista actual
        cambiar_vista(page.navigation_bar.selected_index)

    def eliminar_producto_db(id_prod):
        conn = sqlite3.connect("cocina.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
        conn.commit()
        conn.close()
        cambiar_vista(0) # Volver al inventario

    # --- COMPONENTES DE UI ---

    # Selector de archivos (Cámara/Galería)
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            archivo = e.files[0].path
            imagen_seleccionada.current = archivo
            btn_foto.text = "Foto seleccionada"
            btn_foto.icon = ft.Icons.CHECK
            btn_foto.bgcolor = ft.Colors.GREEN_100
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # Elementos del formulario "Nuevo Producto"
    txt_nombre = ft.TextField(label="Nombre", expand=True)
    txt_cantidad = ft.TextField(label="Cant", width=80, keyboard_type=ft.KeyboardType.NUMBER)
    dd_unidad = ft.Dropdown(width=80, options=[ft.dropdown.Option("un"), ft.dropdown.Option("kg"), ft.dropdown.Option("gr"), ft.dropdown.Option("lt")], value="un")
    btn_foto = ft.ElevatedButton("Tomar Foto / Galería", icon=ft.Icons.CAMERA_ALT, on_click=lambda _: file_picker.pick_files())
    
    def click_guardar_nuevo(e):
        if txt_nombre.value and txt_cantidad.value:
            try:
                guardar_producto(txt_nombre.value, float(txt_cantidad.value), dd_unidad.value, imagen_seleccionada.current)
                # Resetear campos
                txt_nombre.value = ""
                txt_cantidad.value = ""
                imagen_seleccionada.current = None
                btn_foto.text = "Tomar Foto / Galería"
                btn_foto.icon = ft.Icons.CAMERA_ALT
                btn_foto.bgcolor = None
                cambiar_vista(0) # Recargar inventario
            except ValueError:
                pass

    # --- VISTAS (PÁGINAS) ---

    contenedor_principal = ft.Column(scroll="auto", expand=True)

    def vista_inventario():
        productos = obtener_productos()
        items = []
        
        # Formulario de agregar arriba
        form = ft.Container(
            padding=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            content=ft.Column([
                ft.Text("Agregar Nuevo", weight="bold"),
                ft.Row([txt_nombre, txt_cantidad, dd_unidad]),
                btn_foto,
                ft.ElevatedButton("Guardar Producto", bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, on_click=click_guardar_nuevo, width=400)
            ])
        )
        items.append(form)
        items.append(ft.Divider())

        # Lista de productos
        for p in productos:
            p_id, p_nom, p_cant, p_uni, p_img = p
            
            # Imagen o icono por defecto
            img_content = ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=40, color=ft.Colors.GREY)
            if p_img and os.path.exists(p_img):
                img_content = ft.Image(src=p_img, width=50, height=50, fit=ft.ImageFit.COVER, border_radius=5)

            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        img_content,
                        ft.Column([
                            ft.Text(p_nom, weight="bold", size=16),
                            ft.Text(f"Stock: {p_cant} {p_uni}", color=ft.Colors.BLUE if p_cant > 2 else ft.Colors.RED)
                        ], expand=True),
                        ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, id=p_id: eliminar_producto_db(id))
                    ])
                )
            )
            items.append(card)
        return items

    def vista_comida(tipo_comida):
        # Esta función genera la vista para Desayuno, Almuerzo o Cena
        productos = obtener_productos()
        items = [
            ft.Container(padding=10, content=ft.Text(f"Registro de {tipo_comida}", size=20, weight="bold", color=ft.Colors.ORANGE)),
            ft.Container(padding=10, content=ft.Text("Selecciona qué usaste y cuánto:", color=ft.Colors.GREY))
        ]

        for p in productos:
            p_id, p_nom, p_cant, p_uni, p_img = p
            if p_cant > 0: # Solo mostramos si hay stock
                
                # Input para cuanto se usó
                txt_uso = ft.TextField(label="Usado", width=70, height=40, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)
                
                btn_consumir = ft.IconButton(
                    icon=ft.Icons.CHECK_CIRCLE, 
                    icon_color=ft.Colors.GREEN,
                    tooltip="Confirmar consumo",
                    on_click=lambda e, id=p_id, stock=p_cant, input_field=txt_uso: consumir_producto(id, float(input_field.value) if input_field.value else 0, tipo_comida, stock)
                )

                items.append(
                    ft.Container(
                        padding=ft.padding.only(left=10, right=10, bottom=5),
                        content=ft.Row([
                            ft.Text(f"{p_nom}", expand=True, weight="bold"),
                            ft.Text(f"({p_cant} {p_uni})", size=12, color=ft.Colors.GREY),
                            txt_uso,
                            btn_consumir
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                items.append(ft.Divider(height=1, color=ft.Colors.GREY_200))
        return items

    def vista_compras():
        productos = obtener_productos()
        items = [ft.Container(padding=10, content=ft.Text("Lista de Compras", size=20, weight="bold", color=ft.Colors.RED))]
        
        hay_pendientes = False
        for p in productos:
            p_id, p_nom, p_cant, p_uni, p_img = p
            if p_cant <= 0: # Criterio simple: si es 0 o menos
                hay_pendientes = True
                items.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SHOPPING_CART, color=ft.Colors.RED),
                        title=ft.Text(p_nom, weight="bold"),
                        subtitle=ft.Text("¡Se acabó!"),
                    )
                )
        
        if not hay_pendientes:
            items.append(ft.Container(padding=20, content=ft.Text("¡Felicidades! Tienes comida suficiente.", italic=True)))
            
        return items

    # --- NAVEGACIÓN ---

    def cambiar_vista(indice):
        contenedor_principal.controls.clear()
        
        if indice == 0: # Inventario
            contenedor_principal.controls = vista_inventario()
        elif indice == 1: # Desayuno
            contenedor_principal.controls = vista_comida("Desayuno")
        elif indice == 2: # Almuerzo
            contenedor_principal.controls = vista_comida("Almuerzo")
        elif indice == 3: # Cena
            contenedor_principal.controls = vista_comida("Cena")
        elif indice == 4: # Compras
            contenedor_principal.controls = vista_compras()
            
        contenedor_principal.update()

    # CORRECCIÓN AQUI: Usamos NavigationBarDestination
    nav_bar = ft.NavigationBar(
        selected_index=0,
        on_change=lambda e: cambiar_vista(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.INVENTORY_2, label="Inventario"),
            ft.NavigationBarDestination(icon=ft.Icons.COFFEE, label="Desayuno"),
            ft.NavigationBarDestination(icon=ft.Icons.RESTAURANT, label="Almuerzo"),
            ft.NavigationBarDestination(icon=ft.Icons.DINNER_DINING, label="Cena"),
            ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_BAG, label="Compras"),
        ]
    )

    page.add(contenedor_principal)
    page.navigation_bar = nav_bar
    
    # Cargar vista inicial
    cambiar_vista(0)

ft.app(target=main)