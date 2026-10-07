"""
settings_tab.py
===============

Tab "Settings" – user preferences that are persisted in ``config.ini``.

The tab contains its own sub tab view with one sub tab per group:

* **General**   – appearance mode (applied immediately), color theme
                  (needs an app restart), UI language (applied immediately)
                  and "Language Comment": language of the texts_*.xml file
                  names are read from (e.g. "german" -> texts_german.xml;
                  saved with Enter or when the field loses focus)
* **Anno 117**  – GUID ranges of Anno 117
* **Anno 1800** – GUID ranges of Anno 1800

Each game sub tab has two editable range lists:

* **Own GUID Ranges**   – real GUIDs that are assigned and registered
* **Dummy GUID Ranges** – placeholder GUIDs that get replaced

Every list shows one row per range (Start | End | ✕). The "+" button below
a list appends an empty row, "✕" removes a row. "Save Ranges" validates and
stores BOTH lists of that game at once:

* completely empty rows are ignored,
* each list needs at least one range,
* start/end must be non-negative integers with start <= end,
* ranges inside one list must not overlap each other,
* own ranges and dummy ranges of the SAME game must not overlap
  (ranges of different games may overlap – every game has its own database).

The ranges of all games can be edited at any time, independent of the game
currently selected in the game selector.
"""

from tkinter import messagebox

import customtkinter as ctk

from core.config_manager import find_overlap, format_ranges
from core.constants import DEFAULT_COMMENT_LANGUAGE

#: Sub tab key of the general settings (game sub tabs use the game name).
SUBTAB_GENERAL = "settings_general"


class _RangeList:
    """Editable list of GUID ranges: header, one row per range, "+" button.

    Each row is a tuple ``(row_frame, entry_start, entry_end)``.
    """

    def __init__(self, parent, title_font, on_enter):
        """
        :param parent:     frame the list is packed into
        :param title_font: font of the section title
        :param on_enter:   callback (no arguments) triggered by Enter in any entry
        """
        self.on_enter = on_enter
        self.rows = []

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x", padx=10, pady=(10, 0))

        self.lbl_title = ctk.CTkLabel(self.frame, text="", font=title_font)
        self.lbl_title.pack(anchor="w", pady=(0, 4))

        # Column headings "Start" / "End" aligned with the entries below.
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(anchor="w", padx=(20, 0))
        self.lbl_start = ctk.CTkLabel(header, text="", width=140, anchor="w")
        self.lbl_start.pack(side="left", padx=(0, 10))
        self.lbl_end = ctk.CTkLabel(header, text="", width=140, anchor="w")
        self.lbl_end.pack(side="left")

        # Container for the range rows; rows are packed in order.
        self.rows_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.rows_frame.pack(anchor="w", padx=(20, 0))

        # "+" appends an empty row.
        self.btn_add = ctk.CTkButton(self.frame, text="+", width=36, command=self.add_row)
        self.btn_add.pack(anchor="w", padx=(20, 0), pady=(4, 0))

    def set_texts(self, title, start_text, end_text):
        """Apply translated texts to title and column headings."""
        self.lbl_title.configure(text=title)
        self.lbl_start.configure(text=start_text)
        self.lbl_end.configure(text=end_text)

    def add_row(self, start="", end=""):
        """Append a row with two entries and a remove button; focus the start entry."""
        row_frame = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
        row_frame.pack(anchor="w", pady=2)

        entry_start = ctk.CTkEntry(row_frame, width=140)
        entry_start.insert(0, str(start))
        entry_start.pack(side="left", padx=(0, 10))

        entry_end = ctk.CTkEntry(row_frame, width=140)
        entry_end.insert(0, str(end))
        entry_end.pack(side="left", padx=(0, 10))

        row = (row_frame, entry_start, entry_end)
        btn_remove = ctk.CTkButton(
            row_frame, text="✕", width=30, fg_color="#d9534f", hover_color="#c9302c",
            command=lambda: self.remove_row(row),
        )
        btn_remove.pack(side="left")

        for entry in (entry_start, entry_end):
            entry.bind("<Return>", lambda e: self.on_enter())

        self.rows.append(row)
        if start == "":
            entry_start.focus_set()

    def remove_row(self, row):
        """Remove one row from the list (not saved until "Save Ranges")."""
        row[0].destroy()
        self.rows.remove(row)

    def set_ranges(self, ranges):
        """Replace all rows with one row per (start, end) tuple."""
        for row in list(self.rows):
            self.remove_row(row)
        for start, end in ranges:
            self.add_row(start, end)

    def raw_values(self):
        """Return ``[(row_number, start_text, end_text), ...]`` (row numbers start at 1)."""
        return [
            (i, row[1].get().strip(), row[2].get().strip())
            for i, row in enumerate(self.rows, start=1)
        ]


class SettingsTab:
    """Builds and controls the "Settings" tab.

    :param app:    the main :class:`GUIDManagerApp`
    :param parent: the CTkTabview frame this tab is drawn into
    """

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        #: dict game key -> {"own": _RangeList, "dummy": _RangeList, "save": CTkButton}
        self.game_widgets = {}
        self._build_ui()

    # ==================================================================
    # UI construction
    # ==================================================================
    def _build_ui(self):
        """Create the sub tab view: General + one sub tab per game."""
        self.subtabs = ctk.CTkTabview(self.parent)
        self.subtabs.pack(padx=10, pady=10, fill="both", expand=True)

        self._build_general(self.subtabs.add(SUBTAB_GENERAL))
        for key, game in self.app.settings.games.items():
            # Game names are not translated, so they serve as sub tab keys.
            self._build_game(self.subtabs.add(game.name), key)

    def _build_general(self, parent):
        """Sub tab "General": appearance mode, color theme, language."""
        cfg = self.app.settings
        frame = ctk.CTkFrame(parent)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
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

        # Row 3: language of the texts_*.xml file used for names
        self.lbl_comment_lang = ctk.CTkLabel(frame, text="", font=bold)
        self.lbl_comment_lang.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.entry_comment_lang = ctk.CTkEntry(frame, width=140)
        self.entry_comment_lang.insert(0, cfg.comment_language)
        self.entry_comment_lang.grid(row=3, column=1, padx=20, pady=10, sticky="w")
        # Saved without a button: Enter or leaving the field.
        self.entry_comment_lang.bind("<Return>", lambda e: self.save_comment_language())
        self.entry_comment_lang.bind("<FocusOut>", lambda e: self.save_comment_language())

    def _build_game(self, parent, game_key):
        """Sub tab of one game: own range list, dummy range list, save button.

        A scrollable frame is used because the lists can grow with "+".
        """
        game = self.app.settings.games[game_key]
        frame = ctk.CTkScrollableFrame(parent)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        bold = ctk.CTkFont(size=14, weight="bold")

        # "k=game_key" binds the current key (see closures in loops).
        on_enter = lambda k=game_key: self.save_ranges(k)

        own = _RangeList(frame, bold, on_enter)
        own.set_ranges(game.own_ranges)

        dummy = _RangeList(frame, bold, on_enter)
        dummy.set_ranges(game.dummy_ranges)

        btn_save = ctk.CTkButton(
            frame, text="", fg_color="green", hover_color="darkgreen",
            command=on_enter,
        )
        btn_save.pack(anchor="w", padx=30, pady=20)

        self.game_widgets[game_key] = {"own": own, "dummy": dummy, "save": btn_save}

    def update_language(self):
        """Set all texts of this tab according to the active UI language."""
        tr = self.app.tr

        # Rename the "General" sub tab (internal API, see app.update_ui_language).
        try:
            buttons = self.subtabs._segmented_button._buttons_dict
            if SUBTAB_GENERAL in buttons:
                buttons[SUBTAB_GENERAL].configure(text=tr(SUBTAB_GENERAL))
        except Exception as e:
            print(f"Error updating settings sub tab captions: {e}")

        self.lbl_mode.configure(text=tr("settings_appearance"))
        self.lbl_theme.configure(text=tr("settings_theme"))
        self.lbl_lang.configure(text=tr("settings_language"))
        self.lbl_comment_lang.configure(text=tr("settings_comment_language"))

        for widgets in self.game_widgets.values():
            widgets["own"].set_texts(tr("settings_own_ranges"), tr("lbl_range_start"), tr("lbl_range_end"))
            widgets["dummy"].set_texts(tr("settings_dummy_ranges"), tr("lbl_range_start"), tr("lbl_range_end"))
            widgets["save"].configure(text=tr("btn_save_ranges"))

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

    def save_comment_language(self):
        """Store the "Language Comment" field (trimmed, lower case).

        An empty field falls back to English. The normalised value is written
        back into the field; config.ini is only written if the value changed.
        Takes effect with the next registration of a mod.
        """
        value = self.entry_comment_lang.get().strip().lower() or DEFAULT_COMMENT_LANGUAGE
        self.entry_comment_lang.delete(0, "end")
        self.entry_comment_lang.insert(0, value)
        if value != self.app.settings.comment_language:
            self.app.settings.comment_language = value
            self.app.settings.save()

    # ==================================================================
    # GUID ranges
    # ==================================================================
    def _parse_list(self, range_list, label):
        """Read and validate all rows of one :class:`_RangeList`.

        :param label: list name used in error messages (e.g. "Anno 117 – Own GUID Ranges")
        :returns: sorted list of (start, end) tuples, or None after showing an error.
        """
        tr = self.app.tr
        ranges = []
        for row_no, start_text, end_text in range_list.raw_values():
            if not start_text and not end_text:
                continue  # completely empty row -> ignored
            try:
                start, end = int(start_text), int(end_text)
                if start < 0 or end < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", tr("msg_err_range_num").format(label, row_no))
                return None
            if start > end:
                messagebox.showerror("Error", tr("msg_err_range_order").format(label, row_no))
                return None
            ranges.append((start, end))

        if not ranges:
            messagebox.showerror("Error", tr("msg_err_range_empty").format(label))
            return None

        overlap = find_overlap(ranges)
        if overlap:
            messagebox.showerror("Error", tr("msg_err_range_internal_overlap").format(
                label, format_ranges([overlap[0]]), format_ranges([overlap[1]])))
            return None
        return sorted(ranges)

    def save_ranges(self, game_key):
        """Validate and save the own AND dummy ranges of ``game_key``.

        Nothing is stored if any check fails. On success the rows are
        rebuilt in sorted order (empty rows disappear). If the edited game is
        the active one, the Replace tab is notified so it can adjust its
        start GUID, range display and dummy scan.
        """
        tr = self.app.tr
        game = self.app.settings.games[game_key]
        widgets = self.game_widgets[game_key]

        own = self._parse_list(widgets["own"], f"{game.name} – {tr('settings_own_ranges')}")
        if own is None:
            return
        dummy = self._parse_list(widgets["dummy"], f"{game.name} – {tr('settings_dummy_ranges')}")
        if dummy is None:
            return

        overlap = find_overlap(own, dummy)
        if overlap:
            messagebox.showerror("Error", tr("msg_err_overlap").format(
                game.name, format_ranges([overlap[0]]), format_ranges([overlap[1]])))
            return

        game.own_ranges, game.dummy_ranges = own, dummy
        self.app.settings.save()

        widgets["own"].set_ranges(own)
        widgets["dummy"].set_ranges(dummy)

        if game_key == self.app.settings.active_game:
            self.app.replace_tab.on_ranges_changed()

        messagebox.showinfo(
            tr("msg_ranges_saved_title"),
            tr("msg_ranges_saved_body").format(
                game.name, game.own_ranges_text.replace(", ", "\n"),
                game.dummy_ranges_text.replace(", ", "\n"),
            ),
        )
