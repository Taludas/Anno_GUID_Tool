"""
guid_database.py
================

Persistent store of all GUIDs that are already used by the user's mods.

The database is a simple JSON file (see ``DB_FILE``) mapping each GUID
(as string) to the list of mod-relative XML files it was found in::

    {
        "1337471142": ["data/config/export/main/asset/assets.xml"],
        "1337471143": ["data/config/gui/texts_*.xml"]
    }

It serves two purposes:

1. Overview / search of all used GUIDs (tab "GUID Database").
2. Collision avoidance: when real GUIDs are assigned to dummies, every GUID
   that already exists in the database is skipped.
"""

import json
import os

from core.constants import DB_FILE


def guid_sort_key(guid):
    """Sort key that orders numeric GUIDs numerically, others alphabetically.

    Returns a tuple so numbers and strings never get compared directly
    (which would raise a TypeError in Python 3). Numeric GUIDs come first.
    """
    return (0, int(guid), "") if guid.isdigit() else (1, 0, guid)


class GuidDatabase:
    """Wrapper around the JSON GUID database with convenience methods."""

    def __init__(self, path=DB_FILE):
        self.path = path
        #: dict[str, list[str]] – GUID -> list of file locations
        self.entries = self._load()

    # ------------------------------------------------------------------
    # Python protocol helpers (allow "guid in db" and "len(db)")
    # ------------------------------------------------------------------
    def __contains__(self, guid):
        return guid in self.entries

    def __len__(self):
        return len(self.entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self):
        """Load the JSON file. Returns an empty dict if missing or unreadable."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading GUID database: {e}")
            return {}

    def save(self):
        """Write the database to disk (pretty-printed, UTF-8, non-ASCII kept)."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=4, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------
    def add_location(self, guid, location):
        """Register ``guid`` as used in ``location``.

        * New GUID       -> created with ``[location]``; returns True.
        * Existing GUID  -> ``location`` appended if not yet listed; returns False.

        The return value lets callers count how many *new* GUIDs were added.
        """
        if guid not in self.entries:
            self.entries[guid] = [location]
            return True
        if location not in self.entries[guid]:
            self.entries[guid].append(location)
        return False

    def delete(self, guids):
        """Remove all given GUIDs from the database (unknown GUIDs are ignored)."""
        for guid in guids:
            self.entries.pop(guid, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def sorted_items(self):
        """Return ``[(guid, [locations...]), ...]`` sorted by GUID (numeric first)."""
        return [(g, self.entries[g]) for g in sorted(self.entries, key=guid_sort_key)]

    def count_free(self, start, end):
        """Number of GUIDs in [start, end] that are NOT yet registered.

        Computed as "size of range minus used GUIDs inside the range", so it
        is fast even for huge ranges (no iteration over the range itself).
        """
        if start > end:
            return 0
        used = sum(1 for g in self.entries if g.isdigit() and start <= int(g) <= end)
        return (end - start + 1) - used

    def allocate(self, count, start):
        """Return ``count`` free GUIDs (as strings), ascending from ``start``.

        GUIDs already present in the database are skipped, so gaps inside the
        range are filled first. The caller must ensure enough free GUIDs exist
        (see :meth:`count_free`); this method does not check the range end.
        """
        result = []
        current = start
        while len(result) < count:
            if str(current) not in self.entries:
                result.append(str(current))
            current += 1
        return result
