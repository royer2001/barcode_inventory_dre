import tkinter as tk
from tkinter import ttk, messagebox
from db.database import create_connection
from utils.barcode_generator import generate_barcode, generate_barcodes_pdf
import threading


class AutoCompleteEntry(tk.Frame):
    """Entry con autocompletado usando Listbox flotante y botón dropdown."""
    
    def __init__(self, lista, master=None, **kwargs):
        super().__init__(master)
        
        self.lista = lista
        
        # Entry
        self.entry = ttk.Entry(self, **kwargs)
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botón dropdown
        self.dropdown_btn = ttk.Button(
            self, 
            text="▼", 
            width=2,
            command=self.show_all_items
        )
        self.dropdown_btn.pack(side=tk.LEFT)
        
        # Variable
        self.var = tk.StringVar()
        self.entry.config(textvariable=self.var)
        self.var.trace("w", self.update_list)
        
        self.lb = None
        self.lb_frame = None
        
        # Vincular eventos
        self.entry.bind('<Down>', self.on_down)
        self.entry.bind('<Up>', self.on_up)
        self.entry.bind('<Return>', self.on_return)
        self.entry.bind('<Escape>', lambda e: self.close_list())
        self.entry.bind('<FocusOut>', self.on_focus_out)
    
    def show_all_items(self):
        """Mostrar todas las opciones al hacer clic en el botón."""
        self.var.set("")  # Limpiar el entry
        self.update_list_with_items(self.lista)
        self.entry.focus_set()

    def update_list(self, *args):
        """Actualiza la lista de sugerencias mientras se escribe."""
        texto = self.var.get().lower()

        # Cerrar lista si no hay texto
        if texto == "":
            self.close_list()
            return

        # Filtrar coincidencias
        coincidencias = [item for item in self.lista if texto in item.lower()]

        if not coincidencias:
            self.close_list()
            return

        self.update_list_with_items(coincidencias)
    
    def update_list_with_items(self, items):
        """Actualiza el listbox con los items proporcionados."""
        # Crear frame y listbox si no existe
        if self.lb is None:
            # Frame contenedor - usar Toplevel para estar encima de todo
            self.lb_frame = tk.Toplevel(self.winfo_toplevel())
            self.lb_frame.wm_overrideredirect(True)  # Sin bordes de ventana
            self.lb_frame.config(relief=tk.SOLID, borderwidth=1, bg="white")
            
            # Listbox
            self.lb = tk.Listbox(
                self.lb_frame, 
                height=min(8, len(items)),
                selectmode=tk.SINGLE,
                exportselection=False
            )
            self.lb.pack(fill=tk.BOTH, expand=True)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(self.lb_frame, orient=tk.VERTICAL, command=self.lb.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.lb.config(yscrollcommand=scrollbar.set)
            
            # Eventos del listbox
            self.lb.bind('<ButtonRelease-1>', self.select_item)
            self.lb.bind('<Return>', self.select_item)
            self.lb.bind('<Escape>', lambda e: self.close_list())

        # Posicionar debajo del entry (coordenadas absolutas en pantalla)
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        w = self.entry.winfo_width() + self.dropdown_btn.winfo_width()
        
        # Ajustar altura según cantidad de items
        height = min(8, len(items)) * 20 + 4
        
        self.lb_frame.geometry(f"{w}x{height}+{x}+{y}")
        self.lb_frame.lift()

        # Actualizar elementos
        self.lb.delete(0, tk.END)
        for item in items:
            self.lb.insert(tk.END, item)

    def select_item(self, event=None):
        """Selecciona un item del listbox."""
        if self.lb and self.lb.curselection():
            index = self.lb.curselection()[0]
            value = self.lb.get(index)
            self.var.set(value)
            self.close_list()
            
            # Disparar evento de selección
            self.event_generate("<<AutoCompleteSelected>>")
            
            # Mantener foco en el entry
            self.entry.focus_set()

    def on_down(self, event):
        """Navegar hacia abajo en el listbox."""
        if self.lb:
            if not self.lb.curselection():
                self.lb.selection_set(0)
            else:
                current = self.lb.curselection()[0]
                if current < self.lb.size() - 1:
                    self.lb.selection_clear(current)
                    self.lb.selection_set(current + 1)
                    self.lb.see(current + 1)
            return "break"

    def on_up(self, event):
        """Navegar hacia arriba en el listbox."""
        if self.lb and self.lb.curselection():
            current = self.lb.curselection()[0]
            if current > 0:
                self.lb.selection_clear(current)
                self.lb.selection_set(current - 1)
                self.lb.see(current - 1)
            return "break"

    def on_return(self, event):
        """Seleccionar item con Enter."""
        if self.lb and self.lb.curselection():
            self.select_item()
            return "break"
    
    def on_focus_out(self, event):
        """Cerrar lista cuando pierde el foco (con delay para permitir clic)."""
        # Verificar si el clic fue dentro del listbox
        def check_and_close():
            try:
                # Obtener el widget que tiene el foco
                focused = self.focus_get()
                # Si el foco está en el listbox o en el entry, no cerrar
                if focused == self.lb or focused == self.entry:
                    return
                # Si el listbox existe, no cerrar aún
                if self.lb and self.lb.winfo_exists():
                    return
            except:
                pass
            self.close_list()
        
        # Delay para permitir que se complete el clic
        self.after(250, check_and_close)

    def close_list(self):
        """Cerrar y destruir el listbox."""
        if self.lb_frame:
            self.lb_frame.destroy()
            self.lb_frame = None
        if self.lb:
            self.lb = None
    
    def get(self):
        """Obtener el valor actual."""
        return self.var.get()


class MultiOfficeSelector(tk.Toplevel):
    def __init__(self, parent, offices, callback):
        super().__init__(parent)
        self.title("Seleccionar Oficinas")
        self.geometry("500x600")
        self.callback = callback
        self.offices = offices
        self.vars = []
        
        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Botones de control
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Seleccionar Todo", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Deseleccionar Todo", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        
        # Canvas y Scrollbar para la lista
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Guardar referencia a la ventana del canvas para ajustar ancho
        self.canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Ajustar ancho del frame interno al cambiar tamaño del canvas
        def on_canvas_configure(event):
            canvas.itemconfig(self.canvas_window, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)

        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            if event.num == 4:  # Linux scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux scroll down
                canvas.yview_scroll(1, "units")
            else:  # Windows/Mac
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # Vincular eventos de scroll a la ventana y al canvas
        self.bind("<Button-4>", _on_mousewheel)
        self.bind("<Button-5>", _on_mousewheel)
        self.bind("<MouseWheel>", _on_mousewheel)
        
        # Checkboxes
        for office in self.offices:
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.scrollable_frame, text=office, variable=var)
            chk.pack(anchor="w", padx=5, pady=2)
            self.vars.append((office, var))
            
        # Botón Generar
        ttk.Button(self, text="Generar PDF", command=self.on_generate).pack(pady=10)
        
    def select_all(self):
        for _, var in self.vars:
            var.set(True)
            
    def deselect_all(self):
        for _, var in self.vars:
            var.set(False)
            
    def on_generate(self):
        selected = [office for office, var in self.vars if var.get()]
        if not selected:
            messagebox.showwarning("Atención", "Selecciona al menos una oficina.")
            return
        self.callback(selected)
        self.destroy()


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestión de Inventario - Códigos de Barra")
        self.geometry("950x600")
        self.configure(bg="#f8f9fa")

        # Inicializar all_offices ANTES de crear widgets
        self.all_offices = []
        self.load_offices()

        # ======== 🔍 Filtro por oficina + Buscador ========
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        # Filtro por oficina
        ttk.Label(filter_frame, text="Filtrar por oficina:").pack(
            side=tk.LEFT, padx=(0, 10))

        self.office_filter = AutoCompleteEntry(
            self.all_offices,
            filter_frame,
            width=23  # width ahora se pasa al Entry interno
        )
        self.office_filter.pack(side=tk.LEFT)
        self.office_filter.bind("<<AutoCompleteSelected>>", self.filter_by_office)

        ttk.Button(filter_frame, text="Mostrar Todo",
                   command=self.load_data).pack(side=tk.LEFT, padx=10)

        # Buscador global
        ttk.Label(filter_frame, text="Buscar:").pack(
            side=tk.LEFT, padx=(20, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.search_records)

        search_entry = ttk.Entry(
            filter_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))

        # ======== 📋 Tabla ========
        columns = ("codigo_completo", "codigo_patrimonial", "codigo_interno",
                   "detalle_bien", "descripcion", "oficina", "fuente", "tipo_registro")
        self.tree = ttk.Treeview(
            self, columns=columns, show="headings", height=15)

        self.tree.heading("codigo_completo", text="Código Completo")
        self.tree.heading("codigo_patrimonial", text="Código Patrimonial")
        self.tree.heading("codigo_interno", text="Código Interno")
        self.tree.heading("detalle_bien", text="Detalle del Bien")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.heading("oficina", text="Oficina")
        self.tree.heading("fuente", text="Fuente")
        self.tree.heading("tipo_registro", text="Tipo de Registro")

        # Ajuste de anchos
        self.tree.column("codigo_completo", width=140)
        self.tree.column("codigo_patrimonial", width=120)
        self.tree.column("codigo_interno", width=100)
        self.tree.column("detalle_bien", width=240)
        self.tree.column("descripcion", width=160)
        self.tree.column("oficina", width=160)
        self.tree.column("fuente", width=100)
        self.tree.column("tipo_registro", width=120)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Generar Código de Barras (Seleccionado)",
                   command=self.generate_selected_barcode).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Generar PDF (Filtro Actual)",
                   command=self.generate_all_barcodes_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Generar PDF (Selección Múltiple)",
                   command=self.open_multi_office_selector).pack(side=tk.LEFT, padx=5)

        # Cargar todos los datos al iniciar
        self.load_data()

    # ======== 🏢 Cargar oficinas ========
    def load_offices(self):
        """Carga las oficinas únicas desde la BD."""
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT oficina FROM bienes WHERE oficina IS NOT NULL AND oficina != '' ORDER BY oficina ASC")
        self.all_offices = [row[0] for row in cursor.fetchall()]
        conn.close()

    # ======== 📦 Cargar datos ========
    def load_data(self):
        """Carga todos los registros en la tabla."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT codigo_completo, codigo_patrimonial, codigo_interno, detalle_bien, descripcion, oficina, fuente, tipo_registro FROM bienes ORDER BY oficina")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    # ======== 🔍 Filtro por oficina ========
    def filter_by_office(self, event=None):
        """Filtra los registros por oficina seleccionada."""
        selected_office = self.office_filter.get()
        if not selected_office:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT codigo_completo, codigo_patrimonial, codigo_interno, detalle_bien, descripcion, oficina, fuente, tipo_registro FROM bienes WHERE oficina = ?",
            (selected_office,)
        )
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()
    
    # ======== 🧾 Generar código de barras ========
    def generate_selected_barcode(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Atención", "Selecciona un registro.")
            return
        values = self.tree.item(selected, "values")
        codigo = values[0]
        path = generate_barcode(
            codigo,
            title=f"INVENTARIO DRE HUÁNUCO - 2025",
            detalle_bien=values[2],
            logo_path="utils/logo.png",
            save_file=True,
            tipo_registro=values[6]
        )
        messagebox.showinfo("Éxito", f"Código generado:\n{path}")

    def generate_all_barcodes_pdf(self):
        selected_office = self.office_filter.get().strip()
        
        # Si no hay oficina seleccionada, asumimos que son TODAS
        if not selected_office:
            selected_office = "TODAS_LAS_OFICINAS"
        
        records = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            codigo = values[0]
            detalle_bien = values[3]
            oficina = values[5]
            tipo_registro = values[7]
            records.append((codigo, detalle_bien, tipo_registro, oficina))

        if not records:
            messagebox.showwarning("Atención", "No hay registros para generar.")
            return

        self.show_progress_window(len(records))
        thread = threading.Thread(
            target=self._generate_pdf_thread, args=(records,), daemon=True
        )
        thread.start()

    def open_multi_office_selector(self):
        """Abre la ventana de selección múltiple de oficinas."""
        MultiOfficeSelector(self, self.all_offices, self.generate_for_selected_offices)

    def generate_for_selected_offices(self, selected_offices):
        """Genera el PDF para las oficinas seleccionadas."""
        if not selected_offices:
            return

        conn = create_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?'] * len(selected_offices))
        query = f"SELECT codigo_completo, codigo_patrimonial, codigo_interno, detalle_bien, descripcion, oficina, fuente, tipo_registro FROM bienes WHERE oficina IN ({placeholders}) ORDER BY oficina"
        
        cursor.execute(query, selected_offices)
        rows = cursor.fetchall()
        conn.close()

        records = []
        for row in rows:
            # row indices: 0=codigo, 3=detalle, 5=oficina, 7=tipo_registro
            records.append((row[0], row[3], row[7], row[5]))

        if not records:
            messagebox.showwarning("Atención", "No se encontraron registros para las oficinas seleccionadas.")
            return

        self.show_progress_window(len(records))
        
        # Usamos un nombre especial para el archivo
        office_label = "SELECCION_MULTIPLE"
        
        thread = threading.Thread(
            target=self._generate_pdf_thread_custom, args=(records, office_label), daemon=True
        )
        thread.start()

    def _generate_pdf_thread(self, records):
        total = len(records)

        def on_progress(i):
            percent = int((i / total) * 100)
            self.progress_bar["value"] = i
            self.progress_label.config(text=f"{percent}%")
            self.progress_win.update_idletasks()

        path = generate_barcodes_pdf(
            records, progress_callback=on_progress, 
            selected_office=self.office_filter.get())

        self.after(200, self.progress_win.destroy)
        self.after(300, lambda: messagebox.showinfo(
            "Éxito", f"PDF generado correctamente:\n{path}"))

    def _generate_pdf_thread_custom(self, records, label):
        total = len(records)

        def on_progress(i):
            percent = int((i / total) * 100)
            self.progress_bar["value"] = i
            self.progress_label.config(text=f"{percent}%")
            self.progress_win.update_idletasks()

        path = generate_barcodes_pdf(
            records, progress_callback=on_progress, 
            selected_office=label)

        self.after(200, self.progress_win.destroy)
        self.after(300, lambda: messagebox.showinfo(
            "Éxito", f"PDF generado correctamente:\n{path}"))

    # ======== 🔎 Buscador global ========
    def search_records(self, *args):
        search_text = self.search_var.get().lower()

        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT codigo_completo, codigo_patrimonial, codigo_interno, detalle_bien, descripcion, oficina, fuente, tipo_registro FROM bienes")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            if any(search_text in str(value).lower() for value in row):
                self.tree.insert("", tk.END, values=row)

    # ======== BARRA DE PROGRESO ========
    def show_progress_window(self, total):
        self.progress_win = tk.Toplevel(self)
        self.progress_win.title("Generando PDF...")
        self.progress_win.geometry("350x120")
        self.progress_win.resizable(False, False)
        self.progress_win.config(bg="white")

        tk.Label(self.progress_win, text="Generando etiquetas, por favor espere...",
                 bg="white", font=("Arial", 10)).pack(pady=5)

        self.progress_bar = ttk.Progressbar(
            self.progress_win, orient="horizontal", length=300, mode="determinate"
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar["maximum"] = total

        self.progress_label = tk.Label(self.progress_win, text="0%", bg="white")
        self.progress_label.pack()

        self.progress_win.transient(self)
        self.progress_win.grab_set()
        self.update_idletasks()