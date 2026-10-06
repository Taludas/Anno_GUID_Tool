"""
settings_tab.py
===============

Tab "Settings" – user preferences that are persisted in ``config.ini``.

Rows
----
0. Appearance mode   (System / Light / Dark)  – applied immediately
1. Color theme       (blue / green / dark-blue) – needs an app restart
2. Language          (Deutsch / English)       – applied immediately
3. Own GUID range    (Start / End / Save)      – real GUIDs to assign/register
4. Dummy GUID range  (Start / End / Save)      – placeholder GUIDs to replace

Both GUID ranges are validated on save: positive integers, start <= end,
and the two ranges must not overlap.
"""

from tkinter import messagebox

import customtkinter as ctk

from core.config_manager import ranges_overlap


class SettingsTab:
    """Builds and controls the "Settings" tab.

    :param app:    the main :class:`GUIDManagerApp`
    :param parent: the CTkTabview frame this tab is drawn into
    """

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._build_ui()

    # ==================================================================
    # UI construction
    # ==================================================================
    def _build_ui(self):
        """Create all setting rows in a two-column grid (label | control)."""
        cfg = self.app.settings
        frame = ctk.CTkFrame(self.parent)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        bold = ctk.CTkFont(size=14, weight="bold")

        # Row 0: appearance mode
        self.lbl_mode = ctk.CTkLabel(frame, text="", font=bold)
        self.lbl_mode.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.combo_mode = ctk.CTkOptionMenu(
            frame, values=["System", "Light", "Dark"], command=self.change_appearance_mode,
        )
        self.combo_mode.set(cfg.appearance_mode)
        self.combo_mode.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="w")

        # Row 1: color theme
        self.lbl_theme = ctk.CTkLabel(frame, text="", font=bold)
        self.lbl_theme.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.combo_theme = ctk.CTkOptionMenu(
            frame, values=["blue", "green", "dark-blue"], command=self.change_color_theme,
        )
        self.combo_theme.set(cfg.color_theme)
        self.combo_theme.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        # Row 2: language
        self.lbl_lang = ctk.CTkLabel(frame, text="", font=bold)
        self.lbl_lang.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.combo_lang = ctk.CTkOptionMenu(
            frame, values=["Deutsch", "English"], command=self.change_language,
        )
        self.combo_lang.set("Deutsch" if cfg.language == "de" else "English")
        self.combo_lang.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        # Row 3: own GUID range
        (self.lbl_own_range, self.lbl_own_start, self.entry_own_start,
         self.lbl_own_end, self.entry_own_end, self.btn_save_own) = self._build_range_row(
            frame, row=3, start=cfg.own_guid_start, end=cfg.own_guid_end,
            on_save=self.save_own_range,
        )

        # Row 4: dummy GUID range
        (self.lbl_dummy_range, self.lbl_dummy_start, self.entry_dummy_start,
         self.lbl_dummy_end, self.entry_dummy_end, self.btn_save_dummy) = self._build_range_row(
            frame, row=4, start=cfg.dummy_guid_start, end=cfg.dummy_guid_end,
            on_save=self.save_dummy_range,
        )

    @staticmethod
    def _build_range_row(frame, row, start, end, on_save):
        """Create one "<Title>  Start: [___]  End: [___]  [Save]" row.

        Pressing Enter in either entry triggers ``on_save`` as well.
        Returns the created widgets so their texts can be translated later:
        ``(title_label, start_label, start_entry, end_label, end_entry, save_button)``.
        """
        title = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        title.grid(row=row, column=0, padx=20, pady=10, sticky="w")

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.grid(row=row, column=1, padx=20, pady=10, sticky="w")

        lbl_start = ctk.CTkLabel(inner, text="")
        lbl_start.pack(side="left", padx=(0, 5))
        entry_start = ctk.CTkEntry(inner, width=130)
        entry_start.insert(0, str(start))
        entry_start.pack(side="left", padx=(0, 15))

        lbl_end = ctk.CTkLabel(inner, text="")
        lbl_end.pack(side="left", padx=(0, 5))
        entry_end = ctk.CTkEntry(inner, width=130)
        entry_end.insert(0, str(end))
        entry_end.pack(side="left", padx=(0, 15))

        btn_save = ctk.CTkButton(inner, text="", width=100, command=on_save)
        btn_save.pack(side="left")

        entry_start.bind("<Return>", lambda e: on_save())
        entry_end.bind("<Return>", lambda e: on_save())

        return title, lbl_start, entry_start, lbl_end, entry_end, btn_save

    def update_language(self):
        """Set all texts of this tab according to the active UI language."""
        tr = self.app.tr
        self.lbl_mode.configure(text=tr("settings_appearance"))
        self.lbl_theme.configure(text=tr("settings_theme"))
        self.lbl_lang.configure(text=tr("settings_language"))

        self.lbl_own_range.configure(text=tr("settings_guid_range"))
        self.lbl_dummy_range.configure(text=tr("settings_dummy_range"))
        for lbl in (self.lbl_own_start, self.lbl_dummy_start):
            lbl.configure(text=tr("lbl_range_start"))
        for lbl in (self.lbl_own_end, self.lbl_dummy_end):
            lbl.configure(text=tr("lbl_range_end"))
        for btn in (self.btn_save_own, self.btn_save_dummy):
            btn.configure(text=tr("btn_save_range"))

    # ==================================================================
    # Appearance / Theme / Language
    # ==================================================================
    def change_appearance_mode(self, mode):
        """Apply and persist the appearance mode; restyle the database table."""
        ctk.set_appearance_mode(mode)
        self.app.database_tab.apply_treeview_style()
        self.app.settings.appearance_mode = mode
        self.app.settings.save()

    def change_color_theme(self, theme):
        """Persist the color theme. CTk themes only apply fully after a restart."""
        self.app.settings.color_theme = theme
        self.app.settings.save()
        messagebox.showinfo(self.app.tr("msg_theme_restart_title"), self.app.tr("msg_theme_restart_body"))

    def change_language(self, choice):
        """Switch the UI language ("Deutsch" -> "de", otherwise "en")."""
        self.app.set_language("de" if choice == "Deutsch" else "en")

    # ==================================================================
    # GUID ranges
    # ==================================================================
    def _parse_range(self, entry_start, entry_end):
        """Read and validate a (start, end) pair from two entry widgets.

        Shows an error message and returns None if a value is not a
        non-negative integer or if start > end.
        """
        try:
            start = int(entry_start.get().strip())
            end = int(entry_end.get().strip())
            if start < 0 or end < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", self.app.tr("msg_err_range_num"))
            return None
        if start > end:
            messagebox.showerror("Error", self.app.tr("msg_err_range_order"))
            return None
        return start, end

    def save_own_range(self):
        """Validate and save the OWN GUID range.

        Rejected if it overlaps the dummy range. On success the "Replace"
        tab is notified so it can adjust its start GUID and range display.
        """
        cfg = self.app.settings
        parsed = self._parse_range(self.entry_own_start, self.entry_own_end)
        if parsed is None:
            return
        start, end = parsed

        if ranges_overlap(start, end, cfg.dummy_guid_start, cfg.dummy_guid_end):
            messagebox.showerror("Error", self.app.tr("msg_err_overlap").format(
                start, end, cfg.dummy_guid_start, cfg.dummy_guid_end))
            return

        cfg.own_guid_start, cfg.own_guid_end = start, end
        cfg.save()
        self.app.replace_tab.on_own_range_changed()

        messagebox.showinfo(self.app.tr("msg_range_saved_title"),
                            self.app.tr("msg_range_saved_body").format(start, end))

    def save_dummy_range(self):
        """Validate and save the DUMMY GUID range.

        Rejected if it overlaps the own range. On success the "Replace" tab
        is notified so it re-scans the loaded mod with the new range.
        """
        cfg = self.app.settings
        parsed = self._parse_range(self.entry_dummy_start, self.entry_dummy_end)
        if parsed is None:
            return
        start, end = parsed

        if ranges_overlap(start, end, cfg.own_guid_start, cfg.own_guid_end):
            messagebox.showerror("Error", self.app.tr("msg_err_overlap").format(
                cfg.own_guid_start, cfg.own_guid_end, start, end))
            return

        cfg.dummy_guid_start, cfg.dummy_guid_end = start, end
        cfg.save()
        self.app.replace_tab.on_dummy_range_changed()

        messagebox.showinfo(self.app.tr("msg_dummy_saved_title"),
                            self.app.tr("msg_dummy_saved_body").format(start, end))
