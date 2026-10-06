"""
constants.py
============

Global constants shared by all modules of the Anno GUID Tool:
file names, default GUID ranges and the precompiled regular expressions
used to find GUIDs inside Anno XML files.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Program info
# ---------------------------------------------------------------------------

#: Program name and author shown in the window title:
#: "<APP_NAME> <version> by <APP_AUTHOR> - <game>"
APP_NAME = "Anno GUID Tool"
APP_AUTHOR = "gz2k2"


def _program_dir():
    """Directory of the program itself (NOT the current working directory).

    * frozen .exe (PyInstaller): folder containing the .exe
    * normal Python run:         project root (folder of main.py)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#: Possible locations of the text file containing only the program version,
#: e.g. "v1.23.45". The first existing file wins:
#:   1. inside the PyInstaller bundle (sys._MEIPASS) – the one-file .exe
#:      unpacks files added with ``--add-data "version.txt;."`` there
#:   2. next to main.py (normal Python run) or next to the .exe
VERSION_FILES = [
    os.path.join(path, "version.txt")
    for path in (getattr(sys, "_MEIPASS", None), _program_dir())
    if path
]

# ---------------------------------------------------------------------------
# Files (stored next to the working directory the tool is started from)
# ---------------------------------------------------------------------------

#: Legacy single database of older tool versions (before multi-game support).
#: Migrated automatically to the Anno 1800 database on first start.
LEGACY_DB_FILE = "guid_database.json"

#: INI file that stores the user settings (theme, language, GUID ranges, ...).
CONFIG_FILE = "config.ini"

# ---------------------------------------------------------------------------
# Supported games
# ---------------------------------------------------------------------------
#: Every supported game has its own GUID database and its own GUID ranges.
#: Key        = internal identifier (stored in config.ini as "active_game")
#: name       = display name in the UI
#: db_file    = JSON database file of this game
#:              Format: { "<guid>": ["relative/path/assets.xml", ...], ... }
#: section    = INI section in config.ini holding this game's GUID ranges
#: The dict order defines the order of the game selector buttons.
GAMES = {
    "anno117": {
        "name": "Anno 117",
        "db_file": "guid_database_anno117.json",
        "section": "ANNO117",
    },
    "anno1800": {
        "name": "Anno 1800",
        "db_file": "guid_database_anno1800.json",
        "section": "ANNO1800",
    },
}

#: Game that is active when no selection is stored in config.ini yet.
DEFAULT_GAME = "anno1800"

# ---------------------------------------------------------------------------
# Default GUID ranges (used for every game until changed in Settings)
# ---------------------------------------------------------------------------

#: Default start of the user's OWN GUID range (real GUIDs that get assigned).
DEFAULT_GUID_RANGE_START = 1337471142
#: Default end of the user's OWN GUID range (max. signed 32-bit integer).
DEFAULT_GUID_RANGE_END = 2147483647

#: Default start of the DUMMY GUID range (placeholder GUIDs used while modding).
DEFAULT_DUMMY_RANGE_START = 1000000000
#: Default end of the DUMMY GUID range.
DEFAULT_DUMMY_RANGE_END = 1000999999

# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------

#: Matches the value inside <GUID>...</GUID> and <LineId>...</LineId> tags.
#: These tags DEFINE a GUID (assets.xml) or a text line (texts_*.xml).
#: Group 1 = the GUID value (whitespace around it is ignored).
GUID_TAG_PATTERN = re.compile(
    r"<(?:GUID|LineId)>\s*([a-zA-Z0-9_-]+)\s*</(?:GUID|LineId)>",
    re.IGNORECASE,
)

#: Matches every *standalone* number in a text, i.e. a run of digits that is
#: not directly preceded or followed by a letter, digit, underscore or dot.
#: Used to replace dummy GUIDs everywhere (definitions AND references such as
#: <Product>…</Product> or GUID='…' in ModOps) without touching numbers like
#: "10000000012" or "1.1000000001".
NUMBER_PATTERN = re.compile(r"(?<![\w.])(\d+)(?![\w.])")

#: Matches a complete XML comment ``<!-- ... -->`` (also multi-line).
#: Group 1 = the text between the comment markers.
XML_COMMENT_PATTERN = re.compile(r"<!--(.*?)-->", re.DOTALL)

#: Matches ONE "GUID - comment" line inside an XML comment, e.g.
#:     2144009900 - Praefectus Specialists Name
#: Group 1 = GUID, group 2 = comment text.
#:
#: Tolerant on purpose, because these lines are typed by hand or copied
#: from other tools:
#:   * ``[^\S\r\n]`` = any whitespace EXCEPT line breaks, i.e. spaces, tabs
#:     and also non-breaking spaces (U+00A0) from copy & paste
#:   * the separator may be "-" or a Unicode dash (‐ ‑ ‒ – — ― −),
#:     with or without spaces around it
#:   * Windows line endings (\r\n) are handled; the "\r" is not part of the text
#: Works for single-line comments (<!-- 2144009900 - Name -->) and for
#: comment blocks with one "GUID - text" entry per line.
COMMENT_LINE_PATTERN = re.compile(
    r"^[^\S\r\n]*(\d+)[^\S\r\n]*[-\u2010-\u2015\u2212][^\S\r\n]*(.+?)[^\S\r\n]*\r?$",
    re.MULTILINE,
)

#: Matches localisation file names such as "texts_german.xml".
#: All language variants are grouped as "texts_*.xml" in the database.
TEXTS_FILE_PATTERN = re.compile(r"^texts_.*\.xml$", re.IGNORECASE)
