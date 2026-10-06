"""
database_tab.py
===============

Tab "GUID Database" – shows, searches, imports, exports and deletes the
GUIDs registered in ``guid_database.json``.

Features
--------
* **Register Folder / Register ZIP**: scans all XML files of a mod and adds
  every GUID defined in ``<GUID>`` / ``<LineId>`` tags that lies inside the
  user's OWN GUID range (Settings) to the database, together with the file
  it was found in.
* **Search field**: live filter by GUID or file path (on every key release).
* **Export .csv**: writes the whole database to a ``;``-separated CSV
  (UTF-8 with BOM so Excel shows umlauts correctly).
* **Delete**: via button, ``Del`` key or right-click context menu;
  multi-selection supported, ``Ctrl+A`` selects all visible rows.
"""

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.xml_scanner import collect_guids


class DatabaseTab:
    """Builds and controls the "GUID Database" tab.

    :param app:    the main :class:`GUIDManagerApp` (gives access to
                   ``app.settings``, ``app.db``, ``app.tr`` …)
    :param parent: the CTkTabview frame this tab is drawn into
    """

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build_ui()
        self.refresh_view()

    # ==================================================================
    # UI construction
    # ==================================================================
    def _build_ui(self):
        """Create all widgets: toolbar, statistics bar and GUID table."""
        # --- Toolbar (buttons left, search field right) ---------------
        top_frame = ctk.CTkFrame(self.parent)
        top_frame.pack(padx=10, pady=10, fill="x")

        self.btn_import_folder = ctk.CTkButton(top_frame, text="", command=self.import_folder)
        self.btn_import_folder.pack(side="left", padx=5, pady=10)

        self.btn_import_zip = ctk.CTkButton(top_frame, text="", command=self.import_zip)
        self.btn_import_zip.pack(side="left", padx=5, pady=10)

        self.btn_export_csv = ctk.CTkButton(
            top_frame, text="", fg_color="#2b8a3e", hover_color="#216a2f",
            command=self.export_to_csv,
        )
        self.btn_export_csv.pack(side="left", padx=5, pady=10)

        self.btn_delete = ctk.CTkButton(
            top_frame, text="", fg_color="#d9534f", hover_color="#c9302c",
            command=self.delete_selected,
        )
        self.btn_delete.pack(side="left", padx=5, pady=10)

        self.entry_search = ctk.CTkEntry(top_frame, placeholder_text="", width=220)
        self.entry_search.pack(side="right", padx=10, pady=10)
        # Re-filter the table on every key stroke.
        self.entry_search.bind("<KeyRelease>", self.refresh_view)

        # --- Statistics bar ("Registered GUIDs: N") -------------------
        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(padx=10, pady=(5, 5), fill="x")

        self.lbl_stats = ctk.CTkLabel(stats_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_stats.pack(side="left", anchor="w", padx=15, pady=8)

        # --- GUID table (ttk.Treeview, because CTk has no table widget)
        table_container = ctk.CTkFrame(self.parent)
        table_container.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_container, columns=("guid", "location"),
            show="headings", selectmode="extended",
        )
        self.apply_treeview_style()
        self.tree.column("guid", width=200, anchor="w")
        self.tree.column("location", width=750, anchor="w")

        # Keyboard / mouse bindings
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)   # right click
        self.tree.bind("<Control-a>", self.select_all)

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)

    def apply_treeview_style(self):
        """Style the ttk.Treeview to match the current CTk appearance mode.

        ttk widgets do not follow CustomTkinter's light/dark mode
        automatically, so colors are set manually. Called on startup and
        whenever the appearance mode is changed in the Settings tab.
        """
        style = ttk.Style()
        style.theme_use("clam")  # "clam" allows custom heading/background colors

        is_dark = ctk.get_appearance_mode() == "Dark"
        heading_bg = "#2b2b2b" if is_dark else "#e0e0e0"
        text_fg = "#ffffff" if is_dark else "#000000"
        field_bg = "#1e1e1e" if is_dark else "#ffffff"

        style.configure(
            "Treeview", background=field_bg, foreground=text_fg,
            fieldbackground=field_bg, rowheight=25, font=("Consolas", 10),
        )
        style.configure(
            "Treeview.Heading", background=heading_bg, foreground=text_fg,
            font=("Arial", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#1f538d")])

    def update_language(self):
        """Set all texts of this tab according to the active UI language."""
        tr = self.app.tr
        self.btn_import_folder.configure(text=tr("btn_import_folder"))
        self.btn_import_zip.configure(text=tr("btn_import_zip"))
        self.btn_export_csv.configure(text=tr("btn_export_csv"))
        self.btn_delete.configure(text=tr("btn_delete"))
        self.entry_search.configure(placeholder_text=tr("search_ph"))
        self.tree.heading("guid", text=tr("tree_guid"))
        self.tree.heading("location", text=tr("tree_loc"))
        self._update_stats()

    # ==================================================================
    # Table view
    # ==================================================================
    def _update_stats(self):
        """Refresh the "Registered GUIDs: N" label."""
        self.lbl_stats.configure(text=self.app.tr("guids_count").format(len(self.app.db)))

    def refresh_view(self, event=None):
        """Rebuild the table from the database, applying the search filter.

        A row is shown if the (case-insensitive) search text is contained in
        the GUID or in the comma-separated list of file locations.
        ``event`` is unused; it exists so the method can be bound to key events.
        """
        query = self.entry_search.get().lower().strip()
        self._update_stats()

        self.tree.delete(*self.tree.get_children())

        for guid, locations in self.app.db.sorted_items():
            location_str = ", ".join(locations)
            if query and query not in guid.lower() and query not in location_str.lower():
                continue
            self.tree.insert("", "end", values=(guid, location_str))

    def select_all(self, event=None):
        """Select all visible rows (Ctrl+A). Returns "break" to stop default handling."""
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
        return "break"

    def show_context_menu(self, event):
        """Show a right-click menu with a delete entry for the selected rows.

        If the clicked row is not part of the current selection, the
        selection is replaced by that row (standard explorer behaviour).
        The menu label shows the number of rows when more than one is selected.
        """
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if item not in self.tree.selection():
            self.tree.selection_set(item)

        count = len(self.tree.selection())
        label = self.app.tr("btn_delete") + (f" ({count})" if count > 1 else "")

        menu = tk.Menu(self.app, tearoff=0)
        menu.add_command(label=label, command=self.delete_selected)
        menu.post(event.x_root, event.y_root)

    # ==================================================================
    # Delete / Export
    # ==================================================================
    def delete_selected(self):
        """Delete the selected GUIDs from the database after a confirmation."""
        guids = [
            str(self.tree.item(item, "values")[0])
            for item in self.tree.selection()
            if self.tree.item(item, "values")
        ]
        if not guids:
            return

        tr = self.app.tr
        if messagebox.askyesno(tr("msg_confirm_delete_title"),
                               tr("msg_confirm_delete_body").format(len(guids))):
            self.app.db.delete(guids)
            self.app.db.save()
            self.refresh_view()

    def export_to_csv(self):
        """Export the complete database (not only the filtered view) to CSV.

        Columns: GUID ; Location(s). Encoding ``utf-8-sig`` adds a BOM so
        Microsoft Excel detects UTF-8 correctly.
        """
        tr = self.app.tr
        if len(self.app.db) == 0:
            messagebox.showwarning(tr("msg_export_empty_title"), tr("msg_export_empty_body"))
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            title="Export GUID database as CSV",
        )
        if not file_path:  # dialog cancelled
            return

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file, delimiter=";")
                writer.writerow([tr("tree_guid"), tr("tree_loc")])
                for guid, locations in self.app.db.sorted_items():
                    writer.writerow([guid, ", ".join(locations)])
            messagebox.showinfo(tr("msg_export_success_title"), tr("msg_export_success_body"))
        except Exception as e:
            messagebox.showerror("Export error", str(e))

    # ==================================================================
    # Import (register GUIDs of a mod)
    # ==================================================================
    def import_folder(self):
        """Let the user pick a mod FOLDER and register its GUIDs."""
        path = filedialog.askdirectory(title="Select mod folder")
        if path:
            self.register_path(path)

    def import_zip(self):
        """Let the user pick a mod ZIP archive and register its GUIDs."""
        path = filedialog.askopenfilename(
            title="Select mod file (.zip)",
            filetypes=[("ZIP archive", "*.zip"), ("All files", "*.*")],
        )
        if path:
            self.register_path(path)

    def register_path(self, path):
        """Register all OWN-range GUIDs of a mod folder or ZIP in the database.

        Steps:
          1. Scan every XML file and collect GUIDs that pass
             ``config.is_own_guid`` (numeric and inside the own GUID range).
          2. Add each GUID with its file location(s) to the database.
          3. Save the database, refresh the table and show a summary
             (number of scanned XML files / number of NEW GUIDs).

        Also called by the "Replace Dummy GUIDs" tab after a replacement.
        """
        if not path:
            return
        tr = self.app.tr

        try:
            guid_files, xml_count = collect_guids(path, self.app.settings.is_own_guid)
        except Exception as e:  # e.g. corrupt ZIP archive
            messagebox.showerror(tr("msg_err_zip"), str(e))
            return

        new_count = 0
        for guid, files in guid_files.items():
            for location in sorted(files):
                if self.app.db.add_location(guid, location):
                    new_count += 1

        self.app.db.save()
        self.refresh_view()
        messagebox.showinfo(tr("msg_import_title"), tr("msg_import_body").format(xml_count, new_count))
