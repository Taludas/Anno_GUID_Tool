"""
migrate_dialog.py
=================

Small modal dialog for the right-click action "Migrate a mod to a free
GUID…" in the "GUID Database" tab.

Shows the colliding GUID, the mods that define it and the proposed free
GUID. The user picks the mod that should get the new GUID and then selects
that mod's folder or ZIP (the database only stores relative locations, so
the tool cannot know where the mod is on disk).

Mods that define the GUID more than once themselves cannot be migrated
(the tool cannot tell which definition should change); they are shown but
disabled.
"""

import tkinter as tk

import customtkinter as ctk

SOURCE_FOLDER = "folder"
SOURCE_ZIP = "zip"


class MigrateDialog(ctk.CTkToplevel):
    """Ask which mod to migrate and whether it is a folder or a ZIP.

    :param app:      main window (translation, parent)
    :param guid:     the colliding GUID
    :param mods:     mods that define the GUID (in import order)
    :param default:  mod selected initially (normally the last imported one)
    :param blocked:  mods that cannot be migrated (duplicates inside the mod)
    :param proposal: proposed free GUID (display only)
    :param reasons:  extra lines describing the collision (may be empty)

    :meth:`show` returns ``(mod, SOURCE_FOLDER | SOURCE_ZIP)`` or None.
    """

    def __init__(self, app, guid, mods, default, blocked, proposal, reasons=()):
        super().__init__(app)
        self.app = app
        self.result = None
        tr = app.tr
        self.title(tr("mig_title"))
        self.resizable(False, False)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(self, text=tr("mig_heading").format(guid),
                     font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(
            padx=20, pady=(18, 4), fill="x")
        for line in reasons:
            ctk.CTkLabel(self, text=line, anchor="w", justify="left", wraplength=520).pack(
                padx=20, pady=0, fill="x")
        ctk.CTkLabel(self, text=tr("mig_choose_mod"), anchor="w").pack(padx=20, pady=(12, 4), fill="x")

        self.var_mod = tk.StringVar(value=default if default not in blocked else "")
        for mod in mods:
            text = mod + ("   " + tr("mig_blocked") if mod in blocked else "")
            ctk.CTkRadioButton(self, text=text, value=mod, variable=self.var_mod,
                               state="disabled" if mod in blocked else "normal").pack(
                padx=35, pady=3, anchor="w")

        ctk.CTkLabel(self, text=tr("mig_proposal").format(proposal),
                     font=ctk.CTkFont(weight="bold"), text_color=("#2b8a3e", "#6fbf73"),
                     anchor="w").pack(padx=20, pady=(12, 2), fill="x")
        ctk.CTkLabel(self, text=tr("mig_explain"), text_color="gray", anchor="w",
                     justify="left", wraplength=520).pack(padx=20, pady=(0, 8), fill="x")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=20, pady=(8, 18), fill="x")
        ctk.CTkButton(row, text=tr("mig_btn_cancel"), width=100, fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right")
        ctk.CTkButton(row, text=tr("mig_btn_zip"), command=lambda: self._done(SOURCE_ZIP)).pack(
            side="right", padx=(0, 8))
        ctk.CTkButton(row, text=tr("mig_btn_folder"), command=lambda: self._done(SOURCE_FOLDER)).pack(
            side="right", padx=(0, 8))

        self.after(100, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass  # window already closed

    def _done(self, source):
        mod = self.var_mod.get()
        if not mod:
            return   # no (migratable) mod selected
        self.result = (mod, source)
        self.destroy()

    def show(self):
        """Block until the dialog is closed; return ``(mod, source)`` or None."""
        self.wait_window()
        return self.result
