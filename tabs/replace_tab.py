"""
replace_tab.py
==============

Tab "Replace Dummy GUIDs" – replaces placeholder (dummy) GUIDs in a mod
with real, unused GUIDs from the own GUID ranges of the ACTIVE game.
Every game can have several own ranges and several dummy ranges.

Everything in this tab refers to the game selected in the game selector:
its dummy ranges, its own ranges and its database (collision check). When
the game is switched, :meth:`ReplaceTab.on_game_changed` resets the start
GUID and re-scans the loaded mod with the new game's dummy ranges.

Workflow
--------
1. The user opens a mod folder or ZIP ("Open Folder" / "Open ZIP").
2. The mod is scanned immediately; every GUID defined in a ``<GUID>`` or
   ``<LineId>`` tag that lies inside one of the DUMMY GUID ranges (Settings) is
   listed in the log together with the file(s) it is defined in.
3. "Assign & Replace Real GUIDs":
     a. determines the first real GUID to use
        - *Automatic* checked: first GUID of the own GUID ranges
        - otherwise: the value of the "Start GUID" field
     b. checks that enough free GUIDs exist before touching any file,
     c. asks for a final confirmation (OK / Cancel), because the files are
        overwritten directly and the operation cannot be undone,
     d. maps every dummy (sorted ascending) to the next free real GUID
        (GUIDs already in the database are skipped; when an own range is
        full, assignment continues at the start of the next own range),
     e. replaces every standalone occurrence of each dummy in all XML
        files – definitions AND references,
     f. writes a log and offers to register the mod in the database.
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
        game = self.app.game

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
        self.entry_start_guid.insert(0, str(game.first_own_guid))
        self.entry_start_guid.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.lbl_range_info = ctk.CTkLabel(ctrl_frame, text="", text_color="gray")
        self.lbl_range_info.grid(row=2, column=2, padx=10, pady=5, sticky="w")

        # Row 3: "Automatic" checkbox (state persisted in config.ini)
        self.var_auto_assign = tk.BooleanVar(value=self.app.settings.auto_assign)
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
        """Show the active game's own ranges and dummy ranges (from Settings) in this tab."""
        cfg = self.app.game
        self.lbl_range_info.configure(text=self.app.tr("lbl_range_info").format(cfg.own_ranges_text))
        self.lbl_dummy_range_value.configure(text=cfg.dummy_ranges_text)

    # ==================================================================
    # Callbacks from the Settings tab
    # ==================================================================
    def on_game_changed(self):
        """Called after another game was selected in the game selector.

        The start GUID is reset to the first GUID of the new game's own ranges, the range
        display is updated and the loaded mod (if any) is re-scanned with the
        new game's dummy range.
        """
        self._set_start_guid(self.app.game.first_own_guid)
        self.update_range_info()
        if self.working_path:
            self.scan_dummies()

    def on_ranges_changed(self):
        """Called after the GUID ranges of the ACTIVE game were saved in Settings.

        * Start GUID: if it is not a number or lies outside all own ranges,
          it is reset to the first GUID of the own ranges.
        * Range display is updated.
        * The loaded mod (if any) is re-scanned with the new dummy ranges.
        """
        cfg = self.app.game
        try:
            current = int(self.entry_start_guid.get().strip())
        except ValueError:
            current = None
        if current is None or not cfg.is_own_guid(str(current)):
            self._set_start_guid(cfg.first_own_guid)
        self._refresh_after_dummy_change()

    def _refresh_after_dummy_change(self):
        """Update the range display and re-scan the loaded mod (if any),
        so the dummy list reflects the new dummy ranges immediately."""
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
        guid_files, _ = collect_guids(self.working_path, self.app.game.is_dummy_guid)
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
        start GUID, start outside all own ranges, no dummies, not enough free GUIDs)
        or if the user cancels the final "cannot be undone" confirmation.
        """
        tr = self.app.tr
        cfg = self.app.game   # ranges of the active game
        db = self.app.db      # database of the active game

        if not self.working_path:
            messagebox.showwarning("Warning", tr("msg_warn_load_mod"))
            return

        # --- Step 1: determine the first real GUID -------------------
        auto_assign = bool(self.var_auto_assign.get())
        if auto_assign:
            start_guid = cfg.first_own_guid
        else:
            try:
                start_guid = int(self.entry_start_guid.get().strip())
            except ValueError:
                messagebox.showerror("Error", tr("msg_err_num"))
                return

        if not cfg.is_own_guid(str(start_guid)):
            messagebox.showerror("Error", tr("msg_err_start_outside").format(cfg.own_ranges_text))
            return

        # --- Step 2: collect dummies + the files they are defined in --
        try:
            dummy_files = self._collect_dummies()
        except Exception as e:
            messagebox.showerror(tr("msg_err_zip"), str(e))
            return

        if not dummy_files:
            messagebox.showinfo("Info", tr("msg_no_dummies").format(cfg.dummy_ranges_text))
            return

        # --- Step 3: make sure the own ranges have enough free GUIDs ---
        # Counted over ALL own ranges, from the start GUID upwards.
        free_count = db.count_free(cfg.own_ranges, start_guid)
        if free_count < len(dummy_files):
            messagebox.showerror(
                "Error",
                tr("msg_err_range_exhausted").format(cfg.own_ranges_text, len(dummy_files), free_count),
            )
            return

        # --- Step 4: final confirmation (OK / Cancel) ----------------
        # Shown only after all checks passed, so the user is asked only when
        # the replacement can actually run. "Cancel" is the default button to
        # protect against accidental Enter presses. Nothing has been changed yet.
        if not messagebox.askokcancel(
            tr("msg_confirm_replace_title"),
            tr("msg_confirm_replace_body").format(cfg.name, len(dummy_files)),
            icon=messagebox.WARNING,
            default=messagebox.CANCEL,
        ):
            return

        # --- Step 5: map dummies (ascending) to free real GUIDs -------
        sorted_dummies = sorted(dummy_files, key=int)
        # Continues automatically in the next own range when one is full.
        real_guids = db.allocate(len(sorted_dummies), cfg.own_ranges, start_guid)
        dummy_map = dict(zip(sorted_dummies, real_guids))

        # --- Step 6: rewrite all XML files -----------------------------
        try:
            rewrite_xml_files(self.working_path, lambda text: apply_dummy_map(text, dummy_map))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        # Manual mode: move the start GUID behind the last assigned GUID so
        # the next run continues from there (only after a successful rewrite).
        if not auto_assign:
            # If the last GUID was the end of a range, jump to the next range.
            next_guid = cfg.next_own_guid(int(real_guids[-1]) + 1)
            self._set_start_guid(next_guid if next_guid is not None else int(real_guids[-1]) + 1)

        # --- Step 7: log + optional registration in the database ------
        lines = [
            f"Replaced: {dummy:<15} ---> {real:<12} ({', '.join(sorted(dummy_files[dummy]))})\n"
            for dummy, real in dummy_map.items()
        ]
        self._write_log(tr("replace_done"), lines)

        if messagebox.askyesno(tr("msg_ask_db_title"), tr("msg_ask_db_body").format(len(dummy_map), cfg.name)):
            self.app.database_tab.register_path(self.working_path)
