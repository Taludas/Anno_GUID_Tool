"""
constants.py
============

Global constants shared by all modules of the Anno GUID Tool:
file names, default GUID ranges and the precompiled regular expressions
used to find GUIDs inside Anno XML files.
"""

import re

# ---------------------------------------------------------------------------
# Files (stored next to the working directory the tool is started from)
# ---------------------------------------------------------------------------

#: JSON file that stores all registered GUIDs and the files they appear in.
#: Format: { "<guid>": ["relative/path/assets.xml", "texts_*.xml", ...], ... }
DB_FILE = "guid_database.json"

#: INI file that stores the user settings (theme, language, GUID ranges, ...).
CONFIG_FILE = "config.ini"

# ---------------------------------------------------------------------------
# Default GUID ranges
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

#: Matches localisation file names such as "texts_german.xml".
#: All language variants are grouped as "texts_*.xml" in the database.
TEXTS_FILE_PATTERN = re.compile(r"^texts_.*\.xml$", re.IGNORECASE)
