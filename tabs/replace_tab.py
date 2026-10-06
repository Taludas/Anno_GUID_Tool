"""
replace_tab.py
==============

Tab "Replace Dummy GUIDs" – replaces placeholder (dummy) GUIDs in a mod
with real, unused GUIDs from the user's own GUID range.

Workflow
--------
1. The user opens a mod folder or ZIP ("Open Folder" / "Open ZIP").
2. The mod is scanned immediately; every GUID defined in a ``<GUID>`` or
   ``<LineId>`` tag that lies inside the DUMMY GUID range (Settings) is
   listed in the log together with the file(s) it is defined in.
3. "Assign & Replace Real GUIDs":
     a. determines the first real GUID to use
        - *Automatic* checked: start of the own GUID range
        - otherwise: the value of the "Start GUID" field
     b. checks that enough free GUIDs exist before touching any file,
     c. maps every dummy (sorted ascending) to the next free real GUID
        (GUIDs already in the database are skipped),
     d. replaces every standalone occurrence of each dummy in all XML
        files – definitions AND references,
     e. writes a log and offers to register the mod in the database.
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.xml_scanner import apply_dummy_map, collect_guids, rewrite_xml_files


class ReplaceTab:
    """Builds and controls the "Replace Dummy GUIDs" tab.

    :param app:    the main :class:`GUIDManagerApp`
    :param parent: the CTkTabview frame this tab is drawn into
    """

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        #: Currently loaded mod (folder path or ZIP file path), or None.
        self.working_path = None
        self._build_ui()

    # ==================================================================
    # UI construction
    # ==================================================================
    def _build_ui(self):
        """Create all widgets of the tab (grid layout + log textbox)."""
        cfg = self.app.settings

        ctrl_frame = ctk.CTkFrame(self.parent)
        ctrl_frame.pack(padx=10, pady=10, fill="x")

        # Row 0: "Open Folder" / "Open ZIP" buttons + loaded path label
        btn_container = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        btn_container.grid(row=0, column=0, padx=5, pady=10, sticky="w")

        self.btn_select_folder = ctk.CTkButton(btn_container, text="", width=120, command=self.load_folder)
        self.btn_select_folder.pack(side="left", padx=5)

        self.btn_select_zip = ctk.CTkButton(btn_container, text="", width=120, command=self.load_zip)
        self.btn_select_zip.pack(side="left", padx=5)

        self.lbl_mod_path = ctk.CTkLabel(ctrl_frame, text="", text_color="gray")
        self.lbl_mod_path.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Row 1: read-only display of the dummy GUID range (edited in Settings)
        self.lbl_dummy_range = ctk.CTkLabel(ctrl_frame, text="")
        self.lbl_dummy_range.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.lbl_dummy_range_value = ctk.CTkLabel(ctrl_frame, text="")
        self.lbl_dummy_range_value.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Row 2: start GUID entry + own range info
        self.lbl_start = ctk.CTkLabel(ctrl_frame, text="")
        self.lbl_start.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.entry_start_guid = ctk.CTkEntry(ctrl_frame, width=150)
        self.entry_start_guid.insert(0, str(cfg.own_guid_start))
        self.entry_start_guid.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.lbl_range_info = ctk.CTkLabel(ctrl_frame, text="", text_color="gray")
        self.lbl_range_info.grid(row=2, column=2, padx=10, pady=5, sticky="w")

        # Row 3: "Automatic" checkbox (state persisted in config.ini)
        self.var_auto_assign = tk.BooleanVar(value=cfg.auto_assign)
        self.chk_automatic = ctk.CTkCheckBox(
            ctrl_frame, text="", variable=self.var_auto_assign,
            command=self.on_auto_assign_toggled,
        )
        self.chk_automatic.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # Row 4: main action button
        self.btn_replace = ctk.CTkButton(
            ctrl_frame, text="", fg_color="green", hover_color="darkgreen",
            command=self.replace_dummy_guids,
        )
        self.btn_replace.grid(row=4, column=1, padx=10, pady=15, sticky="w")

        # Apply initial enabled/disabled state of the start GUID field
        # without writing the config (nothing changed yet).
        self.on_auto_assign_toggled(save=False)

        # Log output (read-only except while the tool writes into it)
        self.txt_log = ctk.CTkTextbox(
            self.parent, font=ctk.CTkFont(family="Consolas", size=12), wrap="none",
        )
        self.txt_log.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def update_language(self):
        """Set all texts of this tab according to the active UI language."""
        tr = self.app.tr
        self.btn_select_folder.configure(text=tr("btn_load_folder"))
        self.btn_select_zip.configure(text=tr("btn_load_zip"))
        if not self.working_path:
            self.lbl_mod_path.configure(text=tr("no_path"))
        self.lbl_dummy_range.configure(text=tr("lbl_dummy_range"))
        self.lbl_start.configure(text=tr("lbl_start_guid"))
        self.chk_automatic.configure(text=tr("chk_automatic"))
        self.btn_replace.configure(text=tr("btn_replace"))
        self.update_range_info()

    def update_range_info(self):
        """Show the current own range and dummy range (from Settings) in this tab."""
        cfg = self.app.settings
        self.lbl_range_info.configure(
            text=self.app.tr("lbl_range_info").format(cfg.own_guid_start, cfg.own_guid_end)
        )
        self.lbl_dummy_range_value.configure(text=f"{cfg.dummy_guid_start} – {cfg.dummy_guid_end}")

    # ==================================================================
    # Callbacks from the Settings tab
    # ==================================================================
    def on_own_range_changed(self):
        """Called after the own GUID range was changed in Settings.

        If the current start GUID is not a number or lies outside the new
        range, it is reset to the new range start.
        """
        cfg = self.app.settings
        try:
            current = int(self.entry_start_guid.get().strip())
        except ValueError:
            current = None
        if current is None or not (cfg.own_guid_start <= current <= cfg.own_guid_end):
            self._set_start_guid(cfg.own_guid_start)
        self.update_range_info()

    def on_dummy_range_changed(self):
        """Called after the dummy GUID range was changed in Settings.

        Updates the range display and re-scans the loaded mod (if any) so the
        dummy list reflects the new range immediately.
        """
        self.update_range_info()
        if self.working_path:
            self.scan_dummies()

    # ==================================================================
    # Helpers
    # ==================================================================
    def _set_start_guid(self, value):
        """Write ``value`` into the start GUID entry, even if it is disabled."""
        previous_state = self.entry_start_guid.cget("state")
        self.entry_start_guid.configure(state="normal")
        self.entry_start_guid.delete(0, tk.END)
        self.entry_start_guid.insert(0, str(value))
        self.entry_start_guid.configure(state=previous_state)

    def _write_log(self, header, lines):
        """Replace the log content with ``header`` followed by ``lines``.

        The textbox is enabled only while writing so the user cannot edit it.
        """
        self.txt_log.configure(state="normal", wrap="none")
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.insert(tk.END, header)
        for line in lines:
            self.txt_log.insert(tk.END, line)
        self.txt_log.configure(state="disabled")

    def _set_working_path(self, path):
        """Remember the loaded mod, show its path and scan it for dummies."""
        self.working_path = path
        self.lbl_mod_path.configure(text=path, text_color=("black", "white"))
        self.scan_dummies()

    def _collect_dummies(self):
        """Return ``{dummy_guid: {files...}}`` for all dummies in the loaded mod."""
        guid_files, _ = collect_guids(self.working_path, self.app.settings.is_dummy_guid)
        return guid_files

    # ==================================================================
    # Load / Scan
    # ==================================================================
    def load_folder(self):
        """Let the user pick a mod folder and scan it."""
        path = filedialog.askdirectory(title="Select mod folder")
        if path:
            self._set_working_path(path)

    def load_zip(self):
        """Let the user pick a mod ZIP archive and scan it."""
        path = filedialog.askopenfilename(
            title="Select mod file (.zip)",
            filetypes=[("ZIP archive", "*.zip"), ("All files", "*.*")],
        )
        if path:
            self._set_working_path(path)

    def scan_dummies(self):
        """List all dummy GUIDs of the loaded mod in the log (no changes made).

        Output format per line: `` - <dummy>  (<file>, <file>, ...)``,
        sorted numerically by dummy GUID.
        """
        if not self.working_path:
            return
        try:
            dummy_files = self._collect_dummies()
        except Exception as e:
            print(f"Error while scanning: {e}")
            dummy_files = {}

        lines = [
            f" - {d:<15} ({', '.join(sorted(dummy_files[d]))})\n"
            for d in sorted(dummy_files, key=int)
        ]
        self._write_log(self.app.tr("found_dummies").format(len(dummy_files)), lines)

    def on_auto_assign_toggled(self, save=True):
        """Enable/disable the start GUID field depending on "Automatic".

        * Automatic ON  -> field disabled (grey); assignment always starts at
          the beginning of the own range and fills all free gaps.
        * Automatic OFF -> field editable; assignment starts at its value.

        :param save: persist the checkbox state to config.ini (False during
                     initial UI construction).
        """
        if self.var_auto_assign.get():
            self.entry_start_guid.configure(state="disabled", text_color="gray")
        else:
            self.entry_start_guid.configure(state="normal", text_color=("black", "white"))
        if save:
            self.app.settings.auto_assign = bool(self.var_auto_assign.get())
            self.app.settings.save()

    # ==================================================================
    # Main action
    # ==================================================================
    def replace_dummy_guids(self):
        """Assign real GUIDs to all dummies of the loaded mod and rewrite its XML files.

        No file is modified if any validation fails (no mod loaded, invalid
        start GUID, start outside own range, no dummies, not enough free GUIDs).
        """
        tr = self.app.tr
        cfg = self.app.settings
        db = self.app.db

        if not self.working_path:
            messagebox.showwarning("Warning", tr("msg_warn_load_mod"))
            return

        # --- Step 1: determine the first real GUID -------------------
        auto_assign = bool(self.var_auto_assign.get())
        if auto_assign:
            start_guid = cfg.own_guid_start
        else:
            try:
                start_guid = int(self.entry_start_guid.get().strip())
            except ValueError:
                messagebox.showerror("Error", tr("msg_err_num"))
                return

        if not (cfg.own_guid_start <= start_guid <= cfg.own_guid_end):
            messagebox.showerror("Error", tr("msg_err_start_outside").format(cfg.own_guid_start, cfg.own_guid_end))
            return

        # --- Step 2: collect dummies + the files they are defined in --
        try:
            dummy_files = self._collect_dummies()
        except Exception as e:
            messagebox.showerror(tr("msg_err_zip"), str(e))
            return

        if not dummy_files:
            messagebox.showinfo("Info", tr("msg_no_dummies").format(cfg.dummy_guid_start, cfg.dummy_guid_end))
            return

        # --- Step 3: make sure the own range has enough free GUIDs ----
        free_count = db.count_free(start_guid, cfg.own_guid_end)
        if free_count < len(dummy_files):
            messagebox.showerror(
                "Error",
                tr("msg_err_range_exhausted").format(
                    cfg.own_guid_start, cfg.own_guid_end, len(dummy_files), free_count
                ),
            )
            return

        # --- Step 4: map dummies (ascending) to free real GUIDs -------
        sorted_dummies = sorted(dummy_files, key=int)
        real_guids = db.allocate(len(sorted_dummies), start_guid)
        dummy_map = dict(zip(sorted_dummies, real_guids))

        # Manual mode: move the start GUID behind the last assigned GUID so
        # the next run continues from there.
        if not auto_assign:
            self._set_start_guid(int(real_guids[-1]) + 1)

        # --- Step 5: rewrite all XML files -----------------------------
        try:
            rewrite_xml_files(self.working_path, lambda text: apply_dummy_map(text, dummy_map))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        # --- Step 6: log + optional registration in the database ------
        lines = [
            f"Replaced: {dummy:<15} ---> {real:<12} ({', '.join(sorted(dummy_files[dummy]))})\n"
            for dummy, real in dummy_map.items()
        ]
        self._write_log(tr("replace_done"), lines)

        if messagebox.askyesno(tr("msg_ask_db_title"), tr("msg_ask_db_body").format(len(dummy_map))):
            self.app.database_tab.register_path(self.working_path)
