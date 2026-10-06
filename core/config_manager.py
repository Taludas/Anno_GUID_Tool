"""
config_manager.py
=================

Loading, validating and saving of the user settings stored in ``config.ini``.

All settings live in the ``[SETTINGS]`` section:

=================  ==========================================================
Key                Meaning
=================  ==========================================================
appearance_mode    "System", "Light" or "Dark"
color_theme        CustomTkinter color theme ("blue", "green", "dark-blue")
language           UI language ("de" or "en")
auto_assign        "true"/"false" – automatic GUID assignment checkbox
own_guid_start     First GUID of the user's own (real) GUID range
own_guid_end       Last GUID of the user's own (real) GUID range
dummy_guid_start   First GUID of the dummy (placeholder) GUID range
dummy_guid_end     Last GUID of the dummy (placeholder) GUID range
=================  ==========================================================

The rest of the application never touches the INI file directly – it only
reads/writes the attributes of :class:`AppConfig` and calls :meth:`save`.
"""

import configparser
import os

from core.constants import (
    CONFIG_FILE,
    DEFAULT_DUMMY_RANGE_END,
    DEFAULT_DUMMY_RANGE_START,
    DEFAULT_GUID_RANGE_END,
    DEFAULT_GUID_RANGE_START,
)


def ranges_overlap(a_start, a_end, b_start, b_end):
    """Return True if the closed intervals [a_start, a_end] and [b_start, b_end] overlap.

    Two ranges overlap when each one starts before (or exactly when) the other ends.
    Used to make sure the own GUID range and the dummy GUID range never intersect,
    otherwise real GUIDs could be mistaken for dummies (and vice versa).
    """
    return a_start <= b_end and b_start <= a_end


class AppConfig:
    """In-memory representation of ``config.ini``.

    Attributes are plain Python values (str, bool, int). Call :meth:`save`
    after changing them to persist the new state.
    """

    SECTION = "SETTINGS"

    def __init__(self, path=CONFIG_FILE):
        self.path = path
        self._parser = configparser.ConfigParser()

        # Defaults – overwritten by load() if the INI file contains values.
        self.appearance_mode = "System"
        self.color_theme = "blue"
        self.language = "de"
        self.auto_assign = False
        self.own_guid_start = DEFAULT_GUID_RANGE_START
        self.own_guid_end = DEFAULT_GUID_RANGE_END
        self.dummy_guid_start = DEFAULT_DUMMY_RANGE_START
        self.dummy_guid_end = DEFAULT_DUMMY_RANGE_END

        self.load()

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------
    def load(self):
        """Read ``config.ini`` (if present) and populate the attributes.

        Unknown or broken values never crash the app: a broken GUID range
        (non-numeric or start > end) falls back to its default range.
        """
        if os.path.exists(self.path):
            try:
                self._parser.read(self.path, encoding="utf-8")
            except Exception as e:  # corrupt file -> keep defaults
                print(f"Error reading config file: {e}")

        if self.SECTION not in self._parser:
            self._parser[self.SECTION] = {}
        s = self._parser[self.SECTION]

        self.appearance_mode = s.get("appearance_mode", self.appearance_mode)
        self.color_theme = s.get("color_theme", self.color_theme)
        self.language = s.get("language", self.language)
        self.auto_assign = s.get("auto_assign", "false").lower() == "true"

        self.own_guid_start, self.own_guid_end = self._read_range(
            s, "own_guid_start", "own_guid_end",
            DEFAULT_GUID_RANGE_START, DEFAULT_GUID_RANGE_END,
        )
        self.dummy_guid_start, self.dummy_guid_end = self._read_range(
            s, "dummy_guid_start", "dummy_guid_end",
            DEFAULT_DUMMY_RANGE_START, DEFAULT_DUMMY_RANGE_END,
        )

    def save(self):
        """Write all current attribute values back to ``config.ini``.

        Other sections/keys that may exist in the file are preserved because
        the same ConfigParser instance that read the file is written back.
        """
        s = self._parser[self.SECTION]
        s["appearance_mode"] = self.appearance_mode
        s["color_theme"] = self.color_theme
        s["language"] = self.language
        s["auto_assign"] = str(bool(self.auto_assign)).lower()
        s["own_guid_start"] = str(self.own_guid_start)
        s["own_guid_end"] = str(self.own_guid_end)
        s["dummy_guid_start"] = str(self.dummy_guid_start)
        s["dummy_guid_end"] = str(self.dummy_guid_end)

        with open(self.path, "w", encoding="utf-8") as f:
            self._parser.write(f)

    @staticmethod
    def _read_range(section, key_start, key_end, default_start, default_end):
        """Read a (start, end) integer pair from the INI section.

        Returns the defaults if a value is missing, not an integer, or if
        start is greater than end.
        """
        try:
            start = int(section.get(key_start, str(default_start)))
            end = int(section.get(key_end, str(default_end)))
            if start > end:
                raise ValueError("start > end")
            return start, end
        except ValueError:
            return default_start, default_end

    # ------------------------------------------------------------------
    # GUID range helpers
    # ------------------------------------------------------------------
    def is_own_guid(self, guid_str):
        """True if ``guid_str`` is numeric and inside the OWN GUID range.

        Only these GUIDs are registered in the database. Vanilla GUIDs,
        dummy GUIDs and non-numeric placeholders are ignored.
        """
        return guid_str.isdigit() and self.own_guid_start <= int(guid_str) <= self.own_guid_end

    def is_dummy_guid(self, guid_str):
        """True if ``guid_str`` is numeric and inside the DUMMY GUID range.

        Only these GUIDs are replaced with real GUIDs in the "Replace" tab.
        """
        return guid_str.isdigit() and self.dummy_guid_start <= int(guid_str) <= self.dummy_guid_end
