"""
database_tab.py
===============

Tab "GUID Database" – shows, searches, imports, exports and deletes the
GUIDs registered in the database of the ACTIVE game
(``guid_database_anno1800.json`` or ``guid_database_anno117.json``).
Switching the game in the game selector reloads the table via
:meth:`DatabaseTab.refresh_view`; ``app.db`` always points to the active
game's database, so every action below works on that game only.

Features
--------
* **Register Folder / Register ZIP**: scans all XML files of a mod and adds
  every GUID defined in ``<GUID>`` / ``<LineId>`` tags that lies inside the
  OWN GUID range of the active game (Settings) to that game's database, together with the file
  it was found in.
* **Comment column**: shows the comment of a GUID, read from XML comments
  in the format ``GUID - comment`` (e.g. ``2144009900 - Praefectus Name``)
  while registering a mod.
* **Search field**: live filter by GUID, comment or file path (on every key release).
* **Export .csv**: writes the whole database (GUID ; Comment ; Location) to a ``;``-separated CSV
  (UTF-8 with BOM so Excel shows umlauts correctly).
* **Delete**: via button, ``Del`` key or right-click context menu;
  multi-selection supported, ``Ctrl+A`` selects all visible rows.
* **Move to <other game>** (right-click menu): moves the selected entries
  into the database of another game – useful if a mod was registered while
  the wrong game was selected.
"""

import csv
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.xml_scanner import scan_mod

#: Font of the table rows; also used to measure text widths for auto-sizing.
TREE_FONT = ("Consolas", 10)
# ---------------------------------------------------------------------------
# Column widths of the GUID table (all values in pixels)
# ---------------------------------------------------------------------------
# *_WIDTH     = initial width when the table is created
# *_MINWIDTH  = smallest width the user can drag the column to
#
# GUID column: fixed width (GUIDs always have about the same length).
GUID_COL_WIDTH = 90
GUID_COL_MINWIDTH = 80

# Comment column: sized automatically to the longest visible comment after
# every refresh, limited to COMMENT_COL_MIN ... COMMENT_COL_MAX.
COMMENT_COL_MIN = 150
COMMENT_COL_MAX = 450
COMMENT_COL_MINWIDTH = 80

# Location column: sized automatically to the longest visible path, but at
# least the remaining visible width and never smaller than LOCATION_COL_MIN.
LOCATION_COL_WIDTH = 600
LOCATION_COL_MIN = 200
LOCATION_COL_MINWIDTH = 200

# Extra space (pixels) added to measured text widths for the cell margins.
COL_TEXT_PADDING = 20


class DatabaseTab:
    """Builds and controls the "GUID Database" tab.

    :param app:    the main :class:`GUIDManagerApp` (gives access to
                   ``app.game``, ``app.db``, ``app.tr`` …)
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
            table_container, columns=("guid", "comment", "location"),
            show="headings", selectmode="extended",
        )
        self.apply_treeview_style()
        # stretch=False is required for horizontal scrolling: a stretching
        # column always shrinks to the visible width, so the content would
        # never become wider than the table and the x-scrollbar stays inactive.
        # Column order: GUID | Comment | Location.
        # Comment and location widths are adapted to their content after
        # every refresh (see refresh_view / _fit_location_column).
        self.tree.column("guid", width=GUID_COL_WIDTH, minwidth=GUID_COL_MINWIDTH,
                         anchor="w", stretch=False)
        self.tree.column("comment", width=COMMENT_COL_MIN, minwidth=COMMENT_COL_MINWIDTH,
                         anchor="w", stretch=False)
        self.tree.column("location", width=LOCATION_COL_WIDTH, minwidth=LOCATION_COL_MINWIDTH,
                         anchor="w", stretch=False)

        # Keyboard / mouse bindings
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)   # right click
        self.tree.bind("<Control-a>", self.select_all)

        # Vertical + horizontal scrollbars, both linked to the Treeview.
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout:  [ tree | vsb ]
        #               [ hsb  |     ]
        # Only cell (0, 0) grows when the window is resized.
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=(5, 0))
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=(5, 0))
        hsb.grid(row=1, column=0, sticky="ew", padx=(5, 0), pady=(0, 5))
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Shift + mouse wheel scrolls horizontally (Windows: event.delta = ±120).
        self.tree.bind("<Shift-MouseWheel>",
                       lambda e: self.tree.xview_scroll(int(-e.delta / 120), "units"))
        # Re-fit the location column when the table is resized, so it always
        # fills at least the visible area (no empty gap on the right).
        self.tree.bind("<Configure>", lambda e: self._fit_location_column())
        self._location_text_width = 0

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
            fieldbackground=field_bg, rowheight=25, font=TREE_FONT,
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
        # anchor="w" -> column headings left-aligned (ttk default is centered)
        self.tree.heading("guid", text=tr("tree_guid"), anchor="w")
        self.tree.heading("comment", text=tr("tree_comment"), anchor="w")
        self.tree.heading("location", text=tr("tree_loc"), anchor="w")
        self._update_stats()

    # ==================================================================
    # Table view
    # ==================================================================
    def _update_stats(self):
        """Refresh the "Registered GUIDs (<game>): N" label."""
        self.lbl_stats.configure(
            text=self.app.tr("guids_count").format(self.app.game.name, len(self.app.db))
        )

    def refresh_view(self, event=None):
        """Rebuild the table from the database, applying the search filter.

        A row is shown if the (case-insensitive) search text is contained in
        the GUID, the comment or the comma-separated list of file locations.
        ``event`` is unused; it exists so the method can be bound to key events.
        """
        query = self.entry_search.get().lower().strip()
        self._update_stats()

        self.tree.delete(*self.tree.get_children())

        for guid, comment, locations in self.app.db.sorted_items():
            location_str = ", ".join(locations)
            if query and not any(query in text.lower() for text in (guid, comment, location_str)):
                continue
            self.tree.insert("", "end", values=(guid, comment, location_str))

        # Measure the longest visible texts (pixels, Treeview font).
        font = tkfont.Font(family=TREE_FONT[0], size=TREE_FONT[1])
        items = self.tree.get_children()

        def longest(column):
            return max((font.measure(self.tree.set(i, column)) for i in items), default=0)

        # Comment column: fit to the longest comment, but within limits so a
        # very long comment does not push the locations far to the right.
        comment_width = min(max(longest("comment") + COL_TEXT_PADDING, COMMENT_COL_MIN), COMMENT_COL_MAX)
        self.tree.column("comment", width=comment_width)

        self._location_text_width = longest("location")
        self._fit_location_column()

    def _fit_location_column(self):
        """Size the location column so that long paths can be scrolled horizontally.

        Width = max(longest text + padding, remaining visible width).
        * Longer than the view -> the horizontal scrollbar becomes active.
        * Shorter than the view -> the column fills the free space on the right.
        """
        visible = (self.tree.winfo_width()
                   - self.tree.column("guid", "width")
                   - self.tree.column("comment", "width"))
        needed = self._location_text_width + COL_TEXT_PADDING
        self.tree.column("location", width=max(needed, visible, LOCATION_COL_MIN))

    def select_all(self, event=None):
        """Select all visible rows (Ctrl+A). Returns "break" to stop default handling."""
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
        return "break"

    def show_context_menu(self, event):
        """Show the right-click menu for the selected rows.

        Entries:
          * "Move to <game>" – one entry for every game except the active one
          * separator
          * "Delete selected entries"


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
        suffix = f" ({count})" if count > 1 else ""

        menu = tk.Menu(self.app, tearoff=0)

        # One "Move to ..." entry per OTHER game. "k=key" binds the current
        # loop value to the lambda (otherwise every entry would use the last key).
        for key, game in self.app.settings.games.items():
            if key == self.app.settings.active_game:
                continue
            menu.add_command(
                label=self.app.tr("ctx_move_to").format(game.name) + suffix,
                command=lambda k=key: self.move_selected(k),
            )
        menu.add_separator()
        menu.add_command(label=self.app.tr("btn_delete") + suffix, command=self.delete_selected)
        menu.post(event.x_root, event.y_root)

    # ==================================================================
    # Move / Delete / Export
    # ==================================================================
    def _selected_guids(self):
        """Return the GUID strings of all selected table rows."""
        return [
            str(self.tree.item(item, "values")[0])
            for item in self.tree.selection()
            if self.tree.item(item, "values")
        ]

    def move_selected(self, target_key):
        """Move the selected GUIDs from the active game's database to ``target_key``.

        Steps:
          1. Ask for confirmation (Yes / No). The dialog also shows how many
             of the GUIDs lie outside the target game's OWN GUID range,
             because such GUIDs would normally never be registered there.
          2. Move the entries (existing entries in the target are merged).
          3. Save BOTH databases and refresh the table.
          4. Show a summary (moved / merged).
        """
        guids = self._selected_guids()
        if not guids:
            return

        tr = self.app.tr
        source = self.app.game
        target = self.app.settings.games[target_key]
        target_db = self.app.databases[target_key]

        outside = sum(1 for g in guids if not target.is_own_guid(g))
        body = tr("msg_confirm_move_body").format(len(guids), source.name, target.name)
        if outside:
            body += "\n\n" + tr("msg_move_outside_range").format(
                outside, target.name, target.own_ranges_text)

        if not messagebox.askyesno(tr("msg_confirm_move_title"), body, icon=messagebox.WARNING):
            return

        moved, merged = self.app.db.move_to(guids, target_db)
        self.app.db.save()
        target_db.save()
        self.refresh_view()

        messagebox.showinfo(tr("msg_move_done_title"),
                            tr("msg_move_done_body").format(target.name, moved, merged))

    def delete_selected(self):
        """Delete the selected GUIDs from the database after a confirmation."""
        guids = self._selected_guids()
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

        # Suggest a file name containing the game, e.g. "guid_database_anno1800.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"guid_database_{self.app.game.key}.csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            title="Export GUID database as CSV",
        )
        if not file_path:  # dialog cancelled
            return

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file, delimiter=";")
                writer.writerow([tr("tree_guid"), tr("tree_comment"), tr("tree_loc")])
                for guid, comment, locations in self.app.db.sorted_items():
                    writer.writerow([guid, comment, ", ".join(locations)])
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
        """Register all OWN-range GUIDs of a mod folder or ZIP in the ACTIVE game's database.

        Steps:
          1. Scan every XML file and collect GUIDs that pass
             ``app.game.is_own_guid`` (numeric and inside the active game's
             own GUID range).
             At the same time, "GUID - comment" lines inside XML comments
             (``<!-- 2144009900 - Praefectus Name -->``) and fallback names
             (asset ``<Name>`` / text of texts_*.xml) are collected.
          2. Add each GUID with its file location(s) to the active database
             and store its comment, if one was found. A found comment
             overwrites the stored one (the mod is the current source);
             GUIDs without a comment in the mod keep their stored comment.
             Comment priority:
               1. "GUID - comment" line          -> always written
               2. asset <Name>                   -> only if no comment is stored
               3. text from texts_*.xml          -> only if no comment is stored
          3. Save the database, refresh the table and show a summary:
             scanned XML files, NEW GUIDs, and for the comments: found /
             new or changed / unchanged / skipped (GUID not registered,
             e.g. outside the own GUID range or not defined in a
             <GUID>/<LineId> tag of this mod).

        Also called by the "Replace Dummy GUIDs" tab after a replacement.
        """
        if not path:
            return
        tr = self.app.tr

        try:
            guid_files, comments, names, xml_count = scan_mod(path, self.app.game.is_own_guid)
        except Exception as e:  # e.g. corrupt ZIP archive
            messagebox.showerror(tr("msg_err_zip"), str(e))
            return

        new_count = 0
        for guid, files in guid_files.items():
            for location in sorted(files):
                if self.app.db.add_location(guid, location):
                    new_count += 1

        # Comments: only for GUIDs registered by this import.
        changed = unchanged = skipped = 0
        for guid, comment in comments.items():
            if guid not in guid_files:
                skipped += 1
            elif self.app.db.set_comment(guid, comment):
                changed += 1
            else:
                unchanged += 1

        # Fallback names: only for registered GUIDs WITHOUT a "GUID - comment"
        # line in this mod, and only if the database has no comment yet.
        names_set = 0
        for guid, name in names.items():
            if guid in comments:
                continue
            if self.app.db.set_comment_if_empty(guid, name):
                names_set += 1

        self.app.db.save()
        self.refresh_view()
        messagebox.showinfo(
            tr("msg_import_title"),
            tr("msg_import_body").format(
                self.app.game.name, xml_count, new_count,
                len(comments), changed, unchanged, skipped, names_set,
            ),
        )
