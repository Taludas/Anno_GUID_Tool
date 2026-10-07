"""
collision_report.py
===================

Window with the result of "Check Collisions" (tab "GUID Database"):
GUIDs that are defined in more than one of the scanned mods, GUIDs that one
mod defines more than once, GUIDs of the scanned mods that the database
lists for other mods, and GUIDs that are reserved in your Free GUIDs lists.

Read-only – nothing is imported. The list can be exported as CSV.
"""

import csv
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.guid_database import guid_sort_key


class CollisionReport(ctk.CTkToplevel):
    """Show a :class:`FolderScanResult`.

    :param app:    main window (translation, parent)
    :param folder: the scanned folder
    :param result: :class:`FolderScanResult`
    """

    def __init__(self, app, folder, result):
        super().__init__(app)
        self.app = app
        tr = app.tr
        self.title(tr("rep_title"))
        self.geometry("1000x560")
        self.minsize(700, 360)
        self.transient(app)

        # One row per GUID with any kind of collision.
        self.rows = []
        for guid in sorted(result.colliding_guids, key=guid_sort_key):
            kinds, mods, own = [], [], []
            if guid in result.between:
                kinds.append(tr("rep_kind_between"))
                mods += result.between[guid]
            for mod, files in result.duplicates.get(guid, {}).items():
                kinds.append(tr("rep_kind_duplicate").format(len(files)))
                names = ", ".join(sorted({f.rsplit("/", 1)[-1] for f in files}))
                mods.append(f"{mod} ({names})")
            if guid in result.with_db:
                kinds.append(tr("rep_kind_db"))
                own += result.with_db[guid]
            if guid in result.reserved:
                kinds.append(tr("rep_kind_reserved"))
                own += [tr("rep_free_list").format(name) for name in result.reserved[guid]]
            self.rows.append((guid, " + ".join(kinds), ", ".join(mods), ", ".join(own)))

        summary = tr("rep_summary").format(
            folder, len(result.mods), result.xml_count, result.guid_count,
            len(result.between), len(result.duplicates),
            app.game.name, len(result.with_db), len(result.reserved),
        )
        if result.errors:
            summary += "\n" + tr("rep_errors").format(
                "; ".join(f"{path} ({msg})" for path, msg in result.errors))
        ctk.CTkLabel(self, text=summary, anchor="w", justify="left", wraplength=960).pack(
            padx=15, pady=(15, 10), fill="x")

        if not self.rows:
            ctk.CTkLabel(self, text=tr("rep_none"), text_color="#2b8a3e",
                         font=ctk.CTkFont(size=15, weight="bold")).pack(padx=15, pady=20)

        table = ctk.CTkFrame(self)
        table.pack(padx=15, pady=0, fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("guid", "kind", "mods", "db"),
                                 show="headings", selectmode="extended")
        for column, key, width in (("guid", "tree_guid", 100), ("kind", "rep_col_kind", 230),
                                   ("mods", "rep_col_mods", 330), ("db", "rep_col_db", 300)):
            self.tree.heading(column, text=tr(key), anchor="w")
            self.tree.column(column, width=width, minwidth=80, anchor="w")
        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        for row in self.rows:
            self.tree.insert("", "end", values=row)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(padx=15, pady=15, fill="x")
        ctk.CTkButton(bottom, text=tr("rep_btn_close"), fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right")
        ctk.CTkButton(bottom, text=tr("btn_export_csv"), fg_color="#2b8a3e", hover_color="#216a2f",
                      state="normal" if self.rows else "disabled",
                      command=self.export_csv).pack(side="right", padx=(0, 8))

    def export_csv(self):
        """Write the report as ``;``-separated CSV (UTF-8 with BOM, like the database export)."""
        tr = self.app.tr
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv", initialfile="guid_collisions.csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([tr("tree_guid"), tr("rep_col_kind"), tr("rep_col_mods"), tr("rep_col_db")])
                writer.writerows(self.rows)
            messagebox.showinfo(tr("msg_export_success_title"), tr("msg_export_success_body"), parent=self)
        except Exception as e:
            messagebox.showerror("Export error", str(e), parent=self)
