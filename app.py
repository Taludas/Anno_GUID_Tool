"""
app.py
======

Main window of the Anno GUID Tool.

Responsibilities
----------------
* Load the user settings (:class:`AppConfig`) and the GUID database
  (:class:`GuidDatabase`) once and share them with all tabs.
* Create the tab view and the three tabs (order = display order):
    1. "GUID Database"       -> :class:`DatabaseTab`
    2. "Replace Dummy GUIDs" -> :class:`ReplaceTab`
    3. "Settings"            -> :class:`SettingsTab`
* Provide translation (:meth:`tr`) and live language switching.

Tabs communicate with each other only through this object, e.g.
``app.database_tab.register_path(...)`` or ``app.replace_tab.on_own_range_changed()``.
"""

import customtkinter as ctk

from core.config_manager import AppConfig
from core.guid_database import GuidDatabase
from core.translations import TRANSLATIONS
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
        self.title("Anno GUID Tool")
        self.geometry("1050x780")

        # --- Shared state ---------------------------------------------
        #: user settings (config.ini). Named "settings" (not "config")
        #: because tkinter already defines a "config" method on every widget.
        self.settings = AppConfig()
        #: registered GUIDs (guid_database.json)
        self.db = GuidDatabase()

        # Theme must be applied BEFORE widgets are created.
        ctk.set_appearance_mode(self.settings.appearance_mode)
        ctk.set_default_color_theme(self.settings.color_theme)

        # --- Tab view -------------------------------------------------
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        frame_db = self.tabview.add(TAB_KEY_DB)
        frame_assign = self.tabview.add(TAB_KEY_ASSIGN)
        frame_settings = self.tabview.add(TAB_KEY_SETTINGS)

        self.database_tab = DatabaseTab(self, frame_db)
        self.replace_tab = ReplaceTab(self, frame_assign)
        self.settings_tab = SettingsTab(self, frame_settings)

        # Fill all texts for the configured language.
        self.update_ui_language()

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
