"""
app.py
======

Main window of the Anno GUID Tool.

Responsibilities
----------------
* Load the user settings (:class:`AppConfig`) once and ONE GUID database
  (:class:`GuidDatabase`) PER GAME (Anno 117, Anno 1800).
* Show a game selector above the tabs. The selected game decides
    - which database the "GUID Database" tab shows / imports into,
    - which own / dummy GUID range the "Replace Dummy GUIDs" tab uses.
* Create the tab view and the three tabs (order = display order):
    1. "GUID Database"       -> :class:`DatabaseTab`
    2. "Replace Dummy GUIDs" -> :class:`ReplaceTab`
    3. "Settings"            -> :class:`SettingsTab`
* Provide translation (:meth:`tr`) and live language switching.

Tabs communicate with each other only through this object, e.g.
``app.database_tab.register_path(...)`` or ``app.replace_tab.on_ranges_changed()``.

Shortcuts used by the tabs
--------------------------
``app.game`` -> :class:`GameProfile` of the active game (GUID ranges)
``app.db``   -> :class:`GuidDatabase` of the active game
"""

from tkinter import messagebox

import customtkinter as ctk

from core.config_manager import AppConfig
from core.constants import APP_AUTHOR, APP_NAME, GAMES
from core.guid_database import GuidDatabase, migrate_legacy_database
from core.translations import TRANSLATIONS
from core.version import read_version
from tabs.database_tab import DatabaseTab
from tabs.replace_tab import ReplaceTab
from tabs.settings_tab import SettingsTab

# Internal tab identifiers. CTkTabview uses the tab *name* as key, so fixed
# keys are used and only the visible button text is translated later.
TAB_KEY_DB = "tab_db"
TAB_KEY_ASSIGN = "tab_assign"
TAB_KEY_SETTINGS = "tab_settings"


class GUIDManagerApp(ctk.CTk):
    """Root window. Holds shared state and wires the tabs together."""

    def __init__(self):
        super().__init__()
        self.geometry("1050x820")

        #: Program version from version.txt (read once at startup), e.g. "v1.23.45"
        self.version = read_version()

        # --- Shared state ---------------------------------------------
        #: user settings (config.ini). Named "settings" (not "config")
        #: because tkinter already defines a "config" method on every widget.
        self.settings = AppConfig()

        # One-time migration of the old single database -> Anno 1800.
        self._legacy_migrated = migrate_legacy_database("anno1800")

        #: dict game key -> GuidDatabase (one JSON file per game)
        self.databases = {key: GuidDatabase(info["db_file"]) for key, info in GAMES.items()}

        # Theme must be applied BEFORE widgets are created.
        ctk.set_appearance_mode(self.settings.appearance_mode)
        ctk.set_default_color_theme(self.settings.color_theme)

        # --- Game selector (above the tabs) ---------------------------
        game_bar = ctk.CTkFrame(self, fg_color="transparent")
        game_bar.pack(padx=20, pady=(15, 0), fill="x")

        self.lbl_game = ctk.CTkLabel(game_bar, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_game.pack(side="left", padx=(0, 10))

        # Segmented button shows the display names; mapping back to the key
        # is done in _on_game_selected().
        self._name_to_key = {info["name"]: key for key, info in GAMES.items()}
        self.seg_game = ctk.CTkSegmentedButton(
            game_bar, values=list(self._name_to_key), command=self._on_game_selected,
        )
        self.seg_game.set(GAMES[self.settings.active_game]["name"])
        self.seg_game.pack(side="left")

        # --- Tab view -------------------------------------------------
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=(10, 20), fill="both", expand=True)

        frame_db = self.tabview.add(TAB_KEY_DB)
        frame_assign = self.tabview.add(TAB_KEY_ASSIGN)
        frame_settings = self.tabview.add(TAB_KEY_SETTINGS)

        self.database_tab = DatabaseTab(self, frame_db)
        self.replace_tab = ReplaceTab(self, frame_assign)
        self.settings_tab = SettingsTab(self, frame_settings)

        # Fill all texts for the configured language.
        self.update_ui_language()
        self._update_title()

        # Inform the user once about the migrated database (after the
        # window is drawn so the message box has a parent).
        if self._legacy_migrated:
            self.after(200, lambda: messagebox.showinfo(
                self.tr("msg_migrated_title"),
                self.tr("msg_migrated_body").format(GAMES["anno1800"]["db_file"]),
            ))

    # ------------------------------------------------------------------
    # Active game
    # ------------------------------------------------------------------
    @property
    def game(self):
        """:class:`GameProfile` (GUID ranges) of the active game."""
        return self.settings.active

    @property
    def db(self):
        """:class:`GuidDatabase` of the active game."""
        return self.databases[self.settings.active_game]

    def _on_game_selected(self, display_name):
        """Callback of the game selector: switch the active game.

        Persists the choice and refreshes every part of the UI that depends
        on the game (database table, ranges / start GUID / dummy scan in the
        Replace tab, window title).
        """
        key = self._name_to_key[display_name]
        if key == self.settings.active_game:
            return
        self.settings.active_game = key
        self.settings.save()

        self._update_title()
        self.database_tab.refresh_view()
        self.replace_tab.on_game_changed()

    def _update_title(self):
        """Set the window title: "Anno GUID Tool v1.23.45 by gz2k2 - Anno 1800".

        Called at startup and whenever the game is switched. Without a
        readable version.txt the version part is simply left out.
        """
        version = f" {self.version}" if self.version else ""
        self.title(f"{APP_NAME}{version} by {APP_AUTHOR} - {self.game.name}")

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------
    def tr(self, key):
        """Return the UI text for ``key`` in the active language.

        Fallback order: active language -> German -> the key itself.
        """
        lang_dict = TRANSLATIONS.get(self.settings.language, TRANSLATIONS["de"])
        return lang_dict.get(key, TRANSLATIONS["de"].get(key, key))

    def set_language(self, lang):
        """Switch the UI language ("de"/"en"), persist it and refresh all texts."""
        self.settings.language = lang
        self.settings.save()
        self.update_ui_language()

    def update_ui_language(self):
        """Refresh the tab captions and let every tab update its own texts."""
        self.lbl_game.configure(text=self.tr("lbl_game"))

        # CTkTabview has no public API to rename a tab, so the internal
        # segmented button is accessed. Wrapped in try/except in case the
        # internal structure changes in a future CustomTkinter version.
        try:
            buttons = self.tabview._segmented_button._buttons_dict
            for key in (TAB_KEY_DB, TAB_KEY_ASSIGN, TAB_KEY_SETTINGS):
                if key in buttons:
                    buttons[key].configure(text=self.tr(key))
        except Exception as e:
            print(f"Error updating tab captions: {e}")

        self.database_tab.update_language()
        self.replace_tab.update_language()
        self.settings_tab.update_language()
