import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import csv
import os
import sys
import requests
import pandas as pd
from datetime import datetime
from io import StringIO
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────
#  THEME & COLORS
# ─────────────────────────────────────────────
BG_DARK   = "#0D1117"
BG_PANEL  = "#161B22"
BG_INPUT  = "#1C2128"
BG_HOVER  = "#21262D"
ACCENT    = "#238636"
ACCENT2   = "#1F6FEB"
DANGER    = "#DA3633"
WARN      = "#9E6A03"
TEXT_PRI  = "#E6EDF3"
TEXT_SEC  = "#8B949E"
TEXT_MUT  = "#484F58"
BORDER    = "#30363D"
GREEN_DIM = "#3FB950"
BLUE_DIM  = "#58A6FF"
ORANGE    = "#F0883E"

METHOD_COLORS = {
    "GET":    "#3FB950",
    "POST":   "#F0883E",
    "PUT":    "#58A6FF",
    "PATCH":  "#D2A8FF",
    "DELETE": "#FF7B72",
}


class TooltipMixin:
    def add_tooltip(self, widget, text):
        def enter(e):
            self._tip = tk.Toplevel()
            self._tip.wm_overrideredirect(True)
            self._tip.configure(bg=BG_PANEL)
            lbl = tk.Label(self._tip, text=text, bg=BG_PANEL, fg=TEXT_SEC,
                           font=("Consolas", 9), padx=6, pady=3,
                           relief="flat", bd=1)
            lbl.pack()
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            self._tip.wm_geometry(f"+{x}+{y}")
        def leave(e):
            if hasattr(self, "_tip"):
                self._tip.destroy()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)


class StatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK, height=26)
        self.pack_propagate(False)
        self._status = tk.StringVar(value="Listo")
        self._time   = tk.StringVar(value="")
        self._size   = tk.StringVar(value="")

        tk.Label(self, textvariable=self._status, bg=BG_DARK,
                 fg=TEXT_SEC, font=("Consolas", 9), anchor="w").pack(side="left", padx=10)
        tk.Label(self, textvariable=self._size, bg=BG_DARK,
                 fg=TEXT_MUT, font=("Consolas", 9)).pack(side="right", padx=6)
        tk.Label(self, textvariable=self._time, bg=BG_DARK,
                 fg=TEXT_MUT, font=("Consolas", 9)).pack(side="right", padx=6)

    def set(self, msg, color=TEXT_SEC):
        self._status.set(msg)

    def set_meta(self, ms=None, size=None):
        if ms is not None:  self._time.set(f"⏱ {ms} ms")
        if size is not None: self._size.set(f"↓ {size}")


class HeadersTable(tk.Frame):
    """Editable key-value table for headers / params."""
    def __init__(self, parent, label="Headers"):
        super().__init__(parent, bg=BG_PANEL)
        self.rows = []

        top = tk.Frame(self, bg=BG_PANEL)
        top.pack(fill="x", pady=(0, 4))
        tk.Label(top, text=label, bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Consolas", 9, "bold")).pack(side="left")
        tk.Button(top, text="+ Agregar", bg=BG_INPUT, fg=BLUE_DIM,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, activeforeground=BLUE_DIM,
                  command=self._add_row, padx=6).pack(side="right")

        self.container = tk.Frame(self, bg=BG_PANEL)
        self.container.pack(fill="both", expand=True)

        # Header row
        for i, h in enumerate(["Key", "Value", ""]):
            tk.Label(self.container, text=h, bg=BG_PANEL, fg=TEXT_MUT,
                     font=("Consolas", 8), width=(30 if i < 2 else 4)).grid(
                row=0, column=i, sticky="w", padx=2)

        self._add_row()

    def _add_row(self, key="", val=""):
        r = len(self.rows) + 1
        k = tk.Entry(self.container, bg=BG_INPUT, fg=TEXT_PRI,
                     insertbackground=TEXT_PRI, font=("Consolas", 9),
                     relief="flat", bd=4, width=28)
        v = tk.Entry(self.container, bg=BG_INPUT, fg=TEXT_PRI,
                     insertbackground=TEXT_PRI, font=("Consolas", 9),
                     relief="flat", bd=4, width=28)
        k.insert(0, key)
        v.insert(0, val)
        k.grid(row=r, column=0, padx=2, pady=1, sticky="ew")
        v.grid(row=r, column=1, padx=2, pady=1, sticky="ew")

        def del_row(kw=k, vw=v, row_data=None):
            kw.destroy()
            vw.destroy()
            if row_data in self.rows:
                self.rows.remove(row_data)

        btn = tk.Button(self.container, text="✕", bg=BG_PANEL, fg=DANGER,
                        font=("Consolas", 9), bd=0, cursor="hand2",
                        activebackground=BG_PANEL, activeforeground=DANGER)
        row_data = (k, v, btn)
        btn.config(command=lambda rd=row_data: del_row(rd[0], rd[1], rd))
        btn.grid(row=r, column=2, padx=2)
        self.rows.append(row_data)

    def get_dict(self):
        result = {}
        for k, v, _ in self.rows:
            key = k.get().strip()
            val = v.get().strip()
            if key:
                result[key] = val
        return result

    def set_defaults(self, d: dict):
        for k, v, btn in self.rows:
            k.destroy(); v.destroy(); btn.destroy()
        self.rows.clear()
        for key, val in d.items():
            self._add_row(key, val)
        if not d:
            self._add_row()


class SAPClientApp(TooltipMixin):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SAP API Client")
        self.root.geometry("1200x820")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG_DARK)

        self._csv_data = None        # parsed CSV rows for POST body
        self._response_data = None   # last raw response
        self._result_df = None       # last DataFrame

        self._setup_styles()
        self._build_ui()
        self._load_config()

    # ─────────────────────────────────────────────
    #  STYLES
    # ─────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_SEC,
                        padding=[14, 6], font=("Consolas", 9), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_INPUT)],
                  foreground=[("selected", TEXT_PRI)])
        style.configure("Treeview", background=BG_INPUT, fieldbackground=BG_INPUT,
                        foreground=TEXT_PRI, font=("Consolas", 9), rowheight=22,
                        borderwidth=0)
        style.configure("Treeview.Heading", background=BG_PANEL, foreground=TEXT_SEC,
                        font=("Consolas", 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", ACCENT2)])
        style.configure("Vertical.TScrollbar", background=BG_PANEL,
                        troughcolor=BG_DARK, arrowcolor=TEXT_SEC, borderwidth=0)
        style.configure("Horizontal.TScrollbar", background=BG_PANEL,
                        troughcolor=BG_DARK, arrowcolor=TEXT_SEC, borderwidth=0)

    # ─────────────────────────────────────────────
    #  UI BUILD
    # ─────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar ──────────────────────────────
        topbar = tk.Frame(self.root, bg=BG_PANEL, height=48)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="⬡ SAP API CLIENT", bg=BG_PANEL, fg=BLUE_DIM,
                 font=("Consolas", 13, "bold"), padx=14).pack(side="left")

        # Config button
        tk.Button(topbar, text="⚙  Config", bg=BG_PANEL, fg=TEXT_SEC,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, activeforeground=TEXT_PRI,
                  command=self._open_config_dialog, padx=10).pack(side="right", padx=4, pady=8)

        tk.Button(topbar, text="📜  Historial", bg=BG_PANEL, fg=TEXT_SEC,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, activeforeground=TEXT_PRI,
                  command=self._open_history_dialog, padx=10).pack(side="right", padx=4, pady=8)

        tk.Label(topbar, text="v1.0", bg=BG_PANEL, fg=TEXT_MUT,
                 font=("Consolas", 9)).pack(side="right", padx=4)

        # ── URL bar ──────────────────────────────
        urlbar = tk.Frame(self.root, bg=BG_DARK, pady=8)
        urlbar.pack(fill="x", padx=12)

        # Method selector
        self.method_var = tk.StringVar(value="GET")
        self.method_btn = tk.Menubutton(
            urlbar, textvariable=self.method_var,
            bg=BG_INPUT, fg=GREEN_DIM, font=("Consolas", 10, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=10, pady=6,
            activebackground=BG_HOVER)
        self.method_btn.pack(side="left")
        self._build_method_menu()

        # URL entry
        url_frame = tk.Frame(urlbar, bg=BG_INPUT, padx=2)
        url_frame.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(url_frame, textvariable=self.url_var,
                             bg=BG_INPUT, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                             font=("Consolas", 10), relief="flat", bd=6)
        url_entry.pack(fill="x", expand=True)
        url_entry.bind("<Return>", lambda e: self._send_request())

        # Send button
        self.send_btn = tk.Button(
            urlbar, text="  ENVIAR  ", bg=ACCENT, fg="#FFFFFF",
            font=("Consolas", 10, "bold"), relief="flat", bd=0, cursor="hand2",
            activebackground="#2EA043", activeforeground="#FFFFFF",
            command=self._send_request, padx=14, pady=6)
        self.send_btn.pack(side="left", padx=(8, 0))

        # ── Main paned ───────────────────────────
        paned = tk.PanedWindow(self.root, orient="vertical",
                               bg=BORDER, sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # Request panel
        req_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(req_frame, minsize=200)
        self._build_request_panel(req_frame)

        # Response panel
        resp_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(resp_frame, minsize=200)
        self._build_response_panel(resp_frame)

        # ── Status bar ───────────────────────────
        self.statusbar = StatusBar(self.root)
        self.statusbar.pack(fill="x")

    def _build_method_menu(self):
        menu = tk.Menu(self.method_btn, tearoff=0, bg=BG_PANEL, fg=TEXT_PRI,
                       font=("Consolas", 10), activebackground=BG_HOVER,
                       activeforeground=TEXT_PRI, bd=0)
        for m in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            color = METHOD_COLORS.get(m, TEXT_PRI)
            menu.add_command(label=m, foreground=color,
                             command=lambda mm=m: self._set_method(mm))
        self.method_btn["menu"] = menu

    def _set_method(self, method):
        self.method_var.set(method)
        self.method_btn.configure(fg=METHOD_COLORS.get(method, TEXT_PRI))
        # Show/hide body tab
        if method in ("POST", "PUT", "PATCH"):
            self.req_notebook.tab(self.body_tab_idx, state="normal")
        else:
            self.req_notebook.tab(self.body_tab_idx, state="disabled")

    # ─────────────────────────────────────────────
    #  REQUEST PANEL
    # ─────────────────────────────────────────────
    def _build_request_panel(self, parent):
        tk.Label(parent, text="REQUEST", bg=BG_DARK, fg=TEXT_MUT,
                 font=("Consolas", 8, "bold")).pack(anchor="w", padx=4, pady=(4, 0))

        self.req_notebook = ttk.Notebook(parent)
        self.req_notebook.pack(fill="both", expand=True)

        # ── Tab: Auth ────────────────────────────
        auth_tab = tk.Frame(self.req_notebook, bg=BG_PANEL, padx=12, pady=8)
        self.req_notebook.add(auth_tab, text="🔑 Auth")
        self._build_auth_tab(auth_tab)

        # ── Tab: Params ──────────────────────────
        params_tab = tk.Frame(self.req_notebook, bg=BG_PANEL, padx=12, pady=8)
        self.req_notebook.add(params_tab, text="🔗 Params")
        self.params_table = HeadersTable(params_tab, "Query Parameters")
        self.params_table.pack(fill="both", expand=True)
        self.params_table.set_defaults({
            "$select": "",
            "$top": "500",
            "$skip": "0",
            "$filter": "",
        })

        # ── Tab: Headers ─────────────────────────
        headers_tab = tk.Frame(self.req_notebook, bg=BG_PANEL, padx=12, pady=8)
        self.req_notebook.add(headers_tab, text="📋 Headers")
        self.headers_table = HeadersTable(headers_tab, "Request Headers")
        self.headers_table.pack(fill="both", expand=True)
        self.headers_table.set_defaults({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        # ── Tab: Body ────────────────────────────
        body_tab = tk.Frame(self.req_notebook, bg=BG_PANEL, padx=12, pady=8)
        self.req_notebook.add(body_tab, text="📦 Body")
        self.body_tab_idx = self.req_notebook.index("end") - 1
        self._build_body_tab(body_tab)

    def _build_auth_tab(self, parent):
        tk.Label(parent, text="Basic Authentication", bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Consolas", 10, "bold")).pack(anchor="w", pady=(0, 10))

        def field(lbl, show=""):
            row = tk.Frame(parent, bg=BG_PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=lbl, bg=BG_PANEL, fg=TEXT_SEC,
                     font=("Consolas", 9), width=14, anchor="w").pack(side="left")
            var = tk.StringVar()
            e = tk.Entry(row, textvariable=var, bg=BG_INPUT, fg=TEXT_PRI,
                         insertbackground=TEXT_PRI, font=("Consolas", 10),
                         relief="flat", bd=6, show=show)
            e.pack(side="left", fill="x", expand=True)
            return var

        self.host_var     = field("SAP Host")
        self.user_var     = field("Usuario")
        self.password_var = field("Contraseña", show="●")

        # SSL
        self.verify_ssl = tk.BooleanVar(value=True)
        ssl_row = tk.Frame(parent, bg=BG_PANEL)
        ssl_row.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(ssl_row, text="Verificar certificado SSL", variable=self.verify_ssl,
                       bg=BG_PANEL, fg=TEXT_SEC, selectcolor=BG_INPUT,
                       activebackground=BG_PANEL, font=("Consolas", 9),
                       activeforeground=TEXT_PRI).pack(side="left")

        # CSRF Token
        csrf_row = tk.Frame(parent, bg=BG_PANEL)
        csrf_row.pack(fill="x", pady=3)
        self.fetch_csrf = tk.BooleanVar(value=False)
        tk.Checkbutton(csrf_row, text="Obtener CSRF Token automático (para POST/PUT)",
                       variable=self.fetch_csrf,
                       bg=BG_PANEL, fg=TEXT_SEC, selectcolor=BG_INPUT,
                       activebackground=BG_PANEL, font=("Consolas", 9),
                       activeforeground=TEXT_PRI).pack(side="left")

    def _build_body_tab(self, parent):
        # Mode selector
        mode_row = tk.Frame(parent, bg=BG_PANEL)
        mode_row.pack(fill="x", pady=(0, 8))
        self.body_mode = tk.StringVar(value="json")
        for mode, lbl in [("json", "JSON"), ("csv_file", "CSV → JSON"), ("raw", "Raw")]:
            tk.Radiobutton(mode_row, text=lbl, variable=self.body_mode, value=mode,
                           bg=BG_PANEL, fg=TEXT_SEC, selectcolor=BG_INPUT,
                           activebackground=BG_PANEL, font=("Consolas", 9),
                           activeforeground=TEXT_PRI,
                           command=self._refresh_body_ui).pack(side="left", padx=6)

        self.body_stack = tk.Frame(parent, bg=BG_PANEL)
        self.body_stack.pack(fill="both", expand=True)
        self._refresh_body_ui()

    def _refresh_body_ui(self):
        for w in self.body_stack.winfo_children():
            w.destroy()
        mode = self.body_mode.get()

        if mode in ("json", "raw"):
            self.body_text = scrolledtext.ScrolledText(
                self.body_stack, bg=BG_INPUT, fg=TEXT_PRI,
                insertbackground=TEXT_PRI, font=("Consolas", 9),
                relief="flat", bd=0, wrap="none")
            self.body_text.pack(fill="both", expand=True)
            if mode == "json":
                self.body_text.insert("1.0", '{\n  \n}')

        elif mode == "csv_file":
            self._build_csv_panel(self.body_stack)

    def _build_csv_panel(self, parent):
        info = tk.Frame(parent, bg=BG_PANEL)
        info.pack(fill="x", pady=4)
        tk.Label(info, text="Sube un CSV. Cada fila se enviará como objeto JSON en el body.",
                 bg=BG_PANEL, fg=TEXT_SEC, font=("Consolas", 9), wraplength=500).pack(side="left")

        self.csv_file_label = tk.Label(parent, text="No hay archivo seleccionado",
                                       bg=BG_PANEL, fg=TEXT_MUT, font=("Consolas", 9))
        self.csv_file_label.pack(anchor="w", pady=(4, 0))

        btn_row = tk.Frame(parent, bg=BG_PANEL)
        btn_row.pack(fill="x", pady=6)
        tk.Button(btn_row, text="📂  Cargar CSV", bg=BG_INPUT, fg=BLUE_DIM,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, command=self._load_csv,
                  padx=10, pady=4).pack(side="left")
        tk.Button(btn_row, text="✕ Limpiar", bg=BG_INPUT, fg=DANGER,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, command=self._clear_csv,
                  padx=10, pady=4).pack(side="left", padx=6)

        # Preview
        self.csv_preview = scrolledtext.ScrolledText(
            parent, bg=BG_INPUT, fg=TEXT_PRI, insertbackground=TEXT_PRI,
            font=("Consolas", 8), relief="flat", bd=0, height=8, state="disabled")
        self.csv_preview.pack(fill="both", expand=True, pady=(4, 0))

        # Field to template JSON key
        template_row = tk.Frame(parent, bg=BG_PANEL)
        template_row.pack(fill="x", pady=(6, 0))
        tk.Label(template_row, text="JSON wrapper key (opcional):",
                 bg=BG_PANEL, fg=TEXT_SEC, font=("Consolas", 9)).pack(side="left")
        self.csv_wrap_key = tk.Entry(template_row, bg=BG_INPUT, fg=TEXT_PRI,
                                     insertbackground=TEXT_PRI, font=("Consolas", 9),
                                     relief="flat", bd=4, width=20)
        self.csv_wrap_key.pack(side="left", padx=6)
        self.csv_wrap_key.insert(0, "value")

    # ─────────────────────────────────────────────
    #  RESPONSE PANEL
    # ─────────────────────────────────────────────
    def _build_response_panel(self, parent):
        top_row = tk.Frame(parent, bg=BG_DARK)
        top_row.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(top_row, text="RESPONSE", bg=BG_DARK, fg=TEXT_MUT,
                 font=("Consolas", 8, "bold")).pack(side="left")

        self.status_badge = tk.Label(top_row, text="", bg=BG_DARK, fg=GREEN_DIM,
                                     font=("Consolas", 9, "bold"))
        self.status_badge.pack(side="left", padx=8)

        # Export buttons
        tk.Button(top_row, text="⬇  Excel", bg=ACCENT, fg="#FFFFFF",
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground="#2EA043", command=self._export_excel,
                  padx=8, pady=3).pack(side="right", padx=2)
        tk.Button(top_row, text="⬇  CSV", bg=BG_INPUT, fg=BLUE_DIM,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, command=self._export_csv,
                  padx=8, pady=3).pack(side="right", padx=2)
        tk.Button(top_row, text="⬇  JSON", bg=BG_INPUT, fg=ORANGE,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER, command=self._export_json,
                  padx=8, pady=3).pack(side="right", padx=2)

        # Pagination control
        pg_row = tk.Frame(parent, bg=BG_DARK)
        pg_row.pack(fill="x", padx=4, pady=2)
        self.auto_paginate = tk.BooleanVar(value=True)
        tk.Checkbutton(pg_row, text="Auto-paginación OData ($top/$skip)",
                       variable=self.auto_paginate,
                       bg=BG_DARK, fg=TEXT_SEC, selectcolor=BG_INPUT,
                       activebackground=BG_DARK, font=("Consolas", 9),
                       activeforeground=TEXT_PRI).pack(side="left")
        tk.Label(pg_row, text="Tamaño lote:", bg=BG_DARK, fg=TEXT_SEC,
                 font=("Consolas", 9)).pack(side="left", padx=(10, 2))
        self.batch_size = tk.StringVar(value="500")
        tk.Entry(pg_row, textvariable=self.batch_size, bg=BG_INPUT, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, font=("Consolas", 9),
                 relief="flat", bd=4, width=6).pack(side="left")

        resp_nb = ttk.Notebook(parent)
        resp_nb.pack(fill="both", expand=True, pady=(4, 0))

        # Tab: Table
        table_tab = tk.Frame(resp_nb, bg=BG_DARK)
        resp_nb.add(table_tab, text="📊 Tabla")
        self._build_table_tab(table_tab)

        # Tab: Raw JSON
        raw_tab = tk.Frame(resp_nb, bg=BG_DARK)
        resp_nb.add(raw_tab, text="{ } JSON")
        self.raw_text = scrolledtext.ScrolledText(
            raw_tab, bg=BG_INPUT, fg=TEXT_PRI, insertbackground=TEXT_PRI,
            font=("Consolas", 9), relief="flat", bd=0, state="disabled")
        self.raw_text.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab: Log
        log_tab = tk.Frame(resp_nb, bg=BG_DARK)
        resp_nb.add(log_tab, text="📜 Log")
        self.log_text = scrolledtext.ScrolledText(
            log_tab, bg=BG_INPUT, fg=TEXT_SEC, insertbackground=TEXT_PRI,
            font=("Consolas", 8), relief="flat", bd=0, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_table_tab(self, parent):
        controls = tk.Frame(parent, bg=BG_DARK)
        controls.pack(fill="x", padx=4, pady=2)
        tk.Label(controls, text="Filtrar:", bg=BG_DARK, fg=TEXT_SEC,
                 font=("Consolas", 9)).pack(side="left")
        self.table_filter = tk.StringVar()
        self.table_filter.trace_add("write", lambda *_: self._filter_table())
        tk.Entry(controls, textvariable=self.table_filter, bg=BG_INPUT, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, font=("Consolas", 9),
                 relief="flat", bd=4, width=30).pack(side="left", padx=4)

        self.row_count_lbl = tk.Label(controls, text="0 filas", bg=BG_DARK, fg=TEXT_MUT,
                                      font=("Consolas", 9))
        self.row_count_lbl.pack(side="right", padx=6)

        tree_frame = tk.Frame(parent, bg=BG_DARK)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.tree = ttk.Treeview(tree_frame, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    # ─────────────────────────────────────────────
    #  CSV HELPERS
    # ─────────────────────────────────────────────
    def _load_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self._csv_data = [row for row in reader]
            self.csv_file_label.config(
                text=f"✓ {os.path.basename(path)}  ({len(self._csv_data)} filas)",
                fg=GREEN_DIM)
            preview = json.dumps(self._csv_data[:3], indent=2, ensure_ascii=False)
            self.csv_preview.config(state="normal")
            self.csv_preview.delete("1.0", "end")
            self.csv_preview.insert("1.0", preview + "\n... (preview primeras 3 filas)")
            self.csv_preview.config(state="disabled")
            self._log(f"CSV cargado: {len(self._csv_data)} filas, columnas: {list(self._csv_data[0].keys())}")
        except Exception as e:
            messagebox.showerror("Error CSV", str(e))

    def _clear_csv(self):
        self._csv_data = None
        if hasattr(self, "csv_file_label"):
            self.csv_file_label.config(text="No hay archivo seleccionado", fg=TEXT_MUT)
        if hasattr(self, "csv_preview"):
            self.csv_preview.config(state="normal")
            self.csv_preview.delete("1.0", "end")
            self.csv_preview.config(state="disabled")

    # ─────────────────────────────────────────────
    #  REQUEST BUILDER
    # ─────────────────────────────────────────────
    def _get_csrf_token(self, session, base_url):
        try:
            r = session.get(base_url, headers={"x-csrf-token": "fetch"}, timeout=15)
            return r.headers.get("x-csrf-token", "")
        except Exception:
            return ""

    def _build_request_body(self):
        mode = self.body_mode.get()
        if mode == "json" or mode == "raw":
            text = self.body_text.get("1.0", "end").strip()
            if not text or text == "{\n  \n}":
                return None
            return text.encode("utf-8")
        elif mode == "csv_file":
            if not self._csv_data:
                return None
            wrap = self.csv_wrap_key.get().strip()
            if wrap:
                body = {wrap: self._csv_data}
            else:
                body = self._csv_data
            return json.dumps(body, ensure_ascii=False).encode("utf-8")
        return None

    # ─────────────────────────────────────────────
    #  SEND REQUEST
    # ─────────────────────────────────────────────
    def _send_request(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("URL vacía", "Por favor ingresa una URL.")
            return

        # Auto-construct URL from host if relative path given
        if url.startswith("/") or not url.startswith("http"):
            host = self.host_var.get().strip().rstrip("/")
            if host:
                url = f"https://{host}{url if url.startswith('/') else '/' + url}"
                self.url_var.set(url)

        self.send_btn.config(state="disabled", text=" Enviando… ")
        self.statusbar.set("⏳ Enviando solicitud…")
        self._clear_response()

        thread = threading.Thread(target=self._request_worker, args=(url,), daemon=True)
        thread.start()

    def _request_worker(self, url):
        method  = self.method_var.get()
        headers = self.headers_table.get_dict()
        params  = {k: v for k, v in self.params_table.get_dict().items() if v}
        user    = self.user_var.get().strip()
        pwd     = self.password_var.get()
        verify  = self.verify_ssl.get()
        auth    = (user, pwd) if user else None
        do_paginate = self.auto_paginate.get() and method == "GET"
        batch   = int(self.batch_size.get() or 500)
        t0      = datetime.now()

        try:
            session = requests.Session()
            if auth:
                session.auth = auth

            if self.fetch_csrf.get() and method in ("POST", "PUT", "PATCH", "DELETE"):
                token = self._get_csrf_token(session, url)
                if token:
                    headers["x-csrf-token"] = token
                    self._log(f"CSRF Token obtenido: {token[:20]}…")

            all_records = []
            skip = 0
            status_code = None
            response_headers = {}

            while True:
                req_params = dict(params)
                if do_paginate:
                    req_params["$top"]  = str(batch)
                    req_params["$skip"] = str(skip)

                body = self._build_request_body() if method != "GET" else None

                resp = session.request(
                    method, url,
                    headers=headers,
                    params=req_params,
                    data=body,
                    verify=verify,
                    timeout=30)

                status_code = resp.status_code
                response_headers = dict(resp.headers)

                if not resp.ok:
                    self._log(f"Error HTTP {resp.status_code}: {resp.text[:500]}")
                    self.root.after(0, lambda c=resp.status_code: self._show_error(c, resp.text))
                    break

                try:
                    data = resp.json()
                except Exception:
                    # Not JSON (could be XML/text)
                    self.root.after(0, lambda t=resp.text: self._show_raw(t, status_code))
                    break

                # Log estructura para diagnóstico (solo primera página)
                if skip == 0:
                    if isinstance(data, list):
                        self._log(f"Estructura: array externo [{len(data)} elemento(s)]")
                    elif isinstance(data, dict):
                        self._log(f"Estructura: dict keys={list(data.keys())}")

                # ── Detectar estructura OData ──────────────────────────────
                # Estructura 1: {"d": {"results": [...]}}  → OData v2 estándar
                # Estructura 2: {"d": {"results": [...], "__count": "N"}}
                # Estructura 3: {"value": [...]}           → OData v4
                # Estructura 4: [{"d": {"results": [...]}}] → array envolvente (raro)
                # Estructura 5: lista directa              → respuesta plana

                # Desenvolver array externo si existe
                if isinstance(data, list):
                    if len(data) == 1 and isinstance(data[0], dict):
                        data = data[0]
                    else:
                        # Lista directa de registros
                        records = data
                        all_records.extend(records)
                        self._log(f"Lista directa: {len(records)} registros")
                        break

                # Ahora data debe ser dict
                d_node = data.get("d", {})
                if isinstance(d_node, dict):
                    records = d_node.get("results", [])
                    # SAP puede informar el total via __count
                    total_count = d_node.get("__count") or data.get("@odata.count")
                elif isinstance(d_node, list):
                    records = d_node
                    total_count = None
                else:
                    records = data.get("value")
                    total_count = data.get("@odata.count")

                if records is None:
                    # Objeto único
                    all_records = [data]
                    self.root.after(0, lambda d=data, c=status_code: self._show_json(d, c))
                    break

                all_records.extend(records)
                total_str = f" de {total_count}" if total_count else ""
                self._log(f"Página skip={skip}: {len(records)} registros (total acumulado: {len(all_records)}{total_str})")

                # Continuar paginando si el lote vino lleno
                if not do_paginate or len(records) < batch:
                    break
                skip += batch

            elapsed = int((datetime.now() - t0).total_seconds() * 1000)

            if all_records:
                self.root.after(0, lambda r=all_records, c=status_code, ms=elapsed:
                                self._show_results(r, c, ms))
                # Guardar en historial automáticamente
                self._save_to_history(
                    url=url,
                    method=method,
                    params={k: v for k, v in params.items() if v},
                    headers={k: v for k, v in headers.items()
                             if k not in ("Accept", "Content-Type")},
                    rows_count=len(all_records)
                )

        except requests.exceptions.SSLError:
            self._log("Error SSL. Prueba desmarcando 'Verificar SSL'.")
            self.root.after(0, lambda: messagebox.showerror(
                "SSL Error", "Error de certificado SSL.\nDesmarca 'Verificar SSL' en la pestaña Auth."))
        except requests.exceptions.ConnectionError as e:
            self._log(f"Error de conexión: {e}")
            self.root.after(0, lambda: messagebox.showerror("Conexión", str(e)))
        except Exception as e:
            self._log(f"Error inesperado: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.send_btn.config(
                state="normal", text="  ENVIAR  "))

    # ─────────────────────────────────────────────
    #  RESPONSE DISPLAY
    # ─────────────────────────────────────────────
    def _clear_response(self):
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", "end")
        self.raw_text.config(state="disabled")
        for col in self.tree.get_children():
            self.tree.delete(col)
        self.tree["columns"] = ()
        self.status_badge.config(text="")
        self.row_count_lbl.config(text="0 filas")
        self._result_df = None

    def _show_results(self, records, code, ms):
        # Clean OData metadata
        clean = []
        for r in records:
            row = {k: v for k, v in r.items() if k != "__metadata"}
            clean.append(row)

        self._result_df = pd.DataFrame(clean)
        size_str = f"{len(clean)} filas"
        self.statusbar.set(f"✓ {code} OK", color=GREEN_DIM)
        self.statusbar.set_meta(ms=ms, size=size_str)
        self.status_badge.config(text=f"● {code}", fg=GREEN_DIM)
        self.row_count_lbl.config(text=size_str)

        # Populate tree
        cols = list(self._result_df.columns)
        self.tree["columns"] = cols
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=max(80, len(col) * 9), stretch=True)

        for _, row in self._result_df.iterrows():
            vals = [str(row[c]) if pd.notna(row[c]) else "" for c in cols]
            self.tree.insert("", "end", values=vals)

        # Raw JSON
        self._show_raw(json.dumps(clean[:100], indent=2, ensure_ascii=False) +
                       (f"\n\n// ... {len(clean) - 100} más" if len(clean) > 100 else ""), code)
        self._log(f"✓ Completado: {len(clean)} registros en {ms}ms")

    def _show_json(self, data, code):
        text = json.dumps(data, indent=2, ensure_ascii=False)
        self._show_raw(text, code)
        self.status_badge.config(text=f"● {code}", fg=GREEN_DIM)
        self.statusbar.set(f"✓ {code} OK")

    def _show_raw(self, text, code):
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("1.0", text)
        self.raw_text.config(state="disabled")

    def _show_error(self, code, body):
        color = DANGER if code >= 500 else WARN
        self.status_badge.config(text=f"● {code}", fg=color)
        self.statusbar.set(f"✗ Error {code}")
        self._show_raw(body, code)

    def _filter_table(self):
        q = self.table_filter.get().lower()
        if self._result_df is None:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        cols = list(self._result_df.columns)
        count = 0
        for _, row in self._result_df.iterrows():
            vals = [str(row[c]) if pd.notna(row[c]) else "" for c in cols]
            if not q or any(q in v.lower() for v in vals):
                self.tree.insert("", "end", values=vals)
                count += 1
        self.row_count_lbl.config(text=f"{count} filas")

    def _sort_tree(self, col):
        if self._result_df is None:
            return
        asc = getattr(self, "_sort_asc", True)
        self._result_df = self._result_df.sort_values(col, ascending=asc)
        self._sort_asc = not asc
        self._filter_table()

    # ─────────────────────────────────────────────
    #  EXPORT
    # ─────────────────────────────────────────────
    def _export_excel(self):
        if self._result_df is None or self._result_df.empty:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"sap_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        if path:
            self._result_df.to_excel(path, index=False)
            self._log(f"Excel guardado: {path}")
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{path}")

    def _export_csv(self):
        if self._result_df is None or self._result_df.empty:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"sap_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if path:
            self._result_df.to_csv(path, index=False, encoding="utf-8-sig")
            self._log(f"CSV guardado: {path}")
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{path}")

    def _export_json(self):
        raw = self.raw_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"sap_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
            self._log(f"JSON guardado: {path}")
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{path}")

    # ─────────────────────────────────────────────
    #  CONFIG DIALOG
    # ─────────────────────────────────────────────
    def _open_config_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Configuración rápida SAP")
        dlg.configure(bg=BG_PANEL)
        dlg.geometry("560x320")
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="Configuración rápida SAP S/4HANA", bg=BG_PANEL, fg=TEXT_PRI,
                 font=("Consolas", 11, "bold")).pack(pady=(14, 6))

        form = tk.Frame(dlg, bg=BG_PANEL, padx=20)
        form.pack(fill="x")

        def row(lbl, var, show=""):
            f = tk.Frame(form, bg=BG_PANEL)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=lbl, bg=BG_PANEL, fg=TEXT_SEC,
                     font=("Consolas", 9), width=16, anchor="w").pack(side="left")
            e = tk.Entry(f, textvariable=var, bg=BG_INPUT, fg=TEXT_PRI,
                         insertbackground=TEXT_PRI, font=("Consolas", 10),
                         relief="flat", bd=6, show=show)
            e.pack(side="left", fill="x", expand=True)

        row("SAP Host", self.host_var)
        row("Usuario", self.user_var)
        row("Contraseña", self.password_var, show="●")

        # Endpoint templates
        tk.Label(form, text="Endpoint rápido:", bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Consolas", 9)).pack(anchor="w", pady=(10, 2))
        endpoints = [
            ("Business Partners",  "/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner"),
            ("Email Addresses",    "/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_AddressIndependentEmailAddress"),
            ("Sales Orders",       "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder"),
            ("Materials",          "/sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentHeader"),
        ]
        for name, path in endpoints:
            tk.Button(form, text=name, bg=BG_INPUT, fg=BLUE_DIM,
                      font=("Consolas", 9), bd=0, cursor="hand2",
                      activebackground=BG_HOVER,
                      command=lambda p=path: self._set_quick_endpoint(p, dlg),
                      padx=6, pady=2).pack(side="left", padx=2, pady=2)

        btns = tk.Frame(dlg, bg=BG_PANEL)
        btns.pack(pady=14)
        tk.Button(btns, text="Guardar y cerrar", bg=ACCENT, fg="#FFF",
                  font=("Consolas", 10), bd=0, cursor="hand2",
                  activebackground="#2EA043",
                  command=lambda: [self._save_config(), dlg.destroy()],
                  padx=14, pady=6).pack(side="left", padx=6)
        tk.Button(btns, text="Cancelar", bg=BG_INPUT, fg=TEXT_SEC,
                  font=("Consolas", 10), bd=0, cursor="hand2",
                  activebackground=BG_HOVER,
                  command=dlg.destroy, padx=14, pady=6).pack(side="left")

    def _set_quick_endpoint(self, path, dlg):
        host = self.host_var.get().strip().rstrip("/")
        if host:
            self.url_var.set(f"https://{host}{path}")
        else:
            self.url_var.set(path)
        dlg.destroy()

    # ─────────────────────────────────────────────
    #  PERSIST CONFIG
    # ─────────────────────────────────────────────
    def _config_path(self):
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
        return os.path.join(base, "sap_client_config.json")

    def _history_path(self):
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
        return os.path.join(base, "sap_client_history.json")

    def _save_config(self):
        cfg = {
            "host": self.host_var.get(),
            "user": self.user_var.get(),
            "password": self.password_var.get(),
        }
        try:
            with open(self._config_path(), "w") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def _load_config(self):
        try:
            with open(self._config_path()) as f:
                cfg = json.load(f)
            self.host_var.set(cfg.get("host", ""))
            self.user_var.set(cfg.get("user", ""))
            self.password_var.set(cfg.get("password", ""))
            if cfg.get("host"):
                self._log(f"Config cargada: host={cfg['host']}")
        except Exception:
            pass

    # ─────────────────────────────────────────────
    #  HISTORY
    # ─────────────────────────────────────────────
    def _save_to_history(self, url, method, params, headers, rows_count):
        """Guarda la consulta actual en el historial."""
        try:
            history = self._load_history_raw()
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "rows": rows_count,
                "name": ""  # nombre personalizado opcional
            }
            # Evitar duplicados exactos consecutivos
            if history and history[0].get("url") == url and history[0].get("params") == params:
                history[0]["timestamp"] = entry["timestamp"]
                history[0]["rows"] = rows_count
            else:
                history.insert(0, entry)
            # Mantener máximo 50 entradas
            history = history[:50]
            with open(self._history_path(), "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_history_raw(self):
        try:
            with open(self._history_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _open_history_dialog(self):
        history = self._load_history_raw()
        dlg = tk.Toplevel(self.root)
        dlg.title("Historial de consultas")
        dlg.configure(bg=BG_PANEL)
        dlg.geometry("860x520")
        dlg.transient(self.root)
        dlg.grab_set()

        # Header
        hdr = tk.Frame(dlg, bg=BG_PANEL, padx=16, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📜  Historial de consultas", bg=BG_PANEL, fg=TEXT_PRI,
                 font=("Consolas", 11, "bold")).pack(side="left")
        tk.Button(hdr, text="🗑  Limpiar todo", bg=BG_INPUT, fg=DANGER,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER,
                  command=lambda: self._clear_history(dlg), padx=8).pack(side="right")

        if not history:
            tk.Label(dlg, text="No hay consultas guardadas aún.\nRealiza una consulta y se guardará automáticamente.",
                     bg=BG_PANEL, fg=TEXT_MUT, font=("Consolas", 10),
                     justify="center").pack(expand=True)
            return

        # Lista scrollable
        list_frame = tk.Frame(dlg, bg=BG_PANEL)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        canvas = tk.Canvas(list_frame, bg=BG_PANEL, bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG_PANEL)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())
        inner.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        for i, entry in enumerate(history):
            self._build_history_row(inner, entry, i, dlg)

        # Footer
        tk.Label(dlg, text=f"{len(history)} consultas guardadas  ·  máx. 50",
                 bg=BG_PANEL, fg=TEXT_MUT, font=("Consolas", 8)).pack(pady=(0, 6))

    def _build_history_row(self, parent, entry, idx, dlg):
        method = entry.get("method", "GET")
        color  = METHOD_COLORS.get(method, TEXT_PRI)
        ts     = entry.get("timestamp", "")
        url    = entry.get("url", "")
        rows   = entry.get("rows", "?")
        params = entry.get("params", {})

        row = tk.Frame(parent, bg=BG_INPUT, padx=10, pady=8)
        row.pack(fill="x", pady=3, padx=2)

        # Left: method badge + info
        left = tk.Frame(row, bg=BG_INPUT)
        left.pack(side="left", fill="both", expand=True)

        top_line = tk.Frame(left, bg=BG_INPUT)
        top_line.pack(fill="x")
        tk.Label(top_line, text=method, bg=BG_INPUT, fg=color,
                 font=("Consolas", 9, "bold"), width=6).pack(side="left")
        tk.Label(top_line, text=ts, bg=BG_INPUT, fg=TEXT_MUT,
                 font=("Consolas", 8)).pack(side="left", padx=6)
        tk.Label(top_line, text=f"↓ {rows} filas", bg=BG_INPUT, fg=GREEN_DIM,
                 font=("Consolas", 8)).pack(side="left")

        # URL (truncada)
        short_url = url if len(url) < 80 else "…" + url[-77:]
        tk.Label(left, text=short_url, bg=BG_INPUT, fg=TEXT_PRI,
                 font=("Consolas", 9), anchor="w").pack(fill="x", pady=(2, 0))

        # Params preview
        if params:
            param_str = "  ".join(f"{k}={v}" for k, v in params.items() if v)
            if param_str:
                tk.Label(left, text=param_str, bg=BG_INPUT, fg=TEXT_MUT,
                         font=("Consolas", 8), anchor="w").pack(fill="x")

        # Right: buttons
        right = tk.Frame(row, bg=BG_INPUT)
        right.pack(side="right", padx=(8, 0))

        tk.Button(right, text="▶ Cargar", bg=ACCENT2, fg="#FFF",
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground="#388bfd",
                  command=lambda e=entry: self._load_from_history(e, dlg),
                  padx=8, pady=4).pack(pady=2)
        tk.Button(right, text="✕", bg=BG_INPUT, fg=DANGER,
                  font=("Consolas", 9), bd=0, cursor="hand2",
                  activebackground=BG_HOVER,
                  command=lambda i=idx: self._delete_history_entry(i, dlg),
                  padx=6).pack()

    def _load_from_history(self, entry, dlg):
        """Carga una consulta del historial en la UI."""
        self.url_var.set(entry.get("url", ""))
        self._set_method(entry.get("method", "GET"))

        # Restaurar params
        params = entry.get("params", {})
        self.params_table.set_defaults(params)

        # Restaurar headers
        headers = entry.get("headers", {})
        if headers:
            self.headers_table.set_defaults(headers)

        dlg.destroy()
        self._log(f"Consulta cargada desde historial: {entry.get('url', '')[:60]}…")

    def _delete_history_entry(self, idx, dlg):
        history = self._load_history_raw()
        if 0 <= idx < len(history):
            history.pop(idx)
            try:
                with open(self._history_path(), "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        dlg.destroy()
        self._open_history_dialog()

    def _clear_history(self, dlg):
        if messagebox.askyesno("Confirmar", "¿Limpiar todo el historial?"):
            try:
                with open(self._history_path(), "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception:
                pass
            dlg.destroy()

    # ─────────────────────────────────────────────
    #  LOG
    # ─────────────────────────────────────────────
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.config(state="disabled")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.iconbitmap(default="")  # suppress tk icon on Windows
    app = SAPClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()