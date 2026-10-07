"""
guid_database.py
================

Persistent store of all GUIDs that are already used by the user's mods.

Every supported game (see ``GAMES`` in constants.py) has its OWN database
file, e.g. ``guid_database_anno1800.json`` and ``guid_database_anno117.json``.
One :class:`GuidDatabase` instance is created per game.

The database is a JSON file mapping each GUID (as string) to an entry with
the mod-relative XML files it was found in and an optional comment::

    {
        "2144009900": {
            "comment": "Praefectus Specialists Name",
            "locations": ["data/config/gui/texts_*.xml"]
        },
        "1337471142": {
            "comment": "",
            "locations": ["data/config/export/main/asset/assets.xml"]
        }
    }

Older database files stored only the location list per GUID
(``"1337471142": ["assets.xml"]``). They are converted to the new format
automatically when loaded and written in the new format on the next save.

It serves two purposes:

1. Overview / search of all used GUIDs (tab "GUID Database").
2. Collision avoidance: when real GUIDs are assigned to dummies, every GUID
   that already exists in the database is skipped.
"""

import json
import os
import shutil

from core.constants import GAMES, LEGACY_DB_FILE


def guid_sort_key(guid):
    """Sort key that orders numeric GUIDs numerically, others alphabetically.

    Returns a tuple so numbers and strings never get compared directly
    (which would raise a TypeError in Python 3). Numeric GUIDs come first.
    """
    return (0, int(guid), "") if guid.isdigit() else (1, 0, guid)


def _new_entry(locations=None, comment=""):
    """Create a database entry dict in the current format."""
    return {"comment": comment or "", "locations": list(locations or [])}


def _normalize_entry(value):
    """Convert an entry read from JSON into the current dict format.

    * old format: ``["a.xml", "b.xml"]``            -> ``{"comment": "", "locations": [...]}``
    * new format: ``{"comment": ..., "locations": ...}`` -> missing keys are added
    * anything else (corrupt data)                   -> empty entry
    """
    if isinstance(value, list):
        return _new_entry(value)
    if isinstance(value, dict):
        return _new_entry(value.get("locations", []), value.get("comment", ""))
    return _new_entry()


class GuidDatabase:
    """Wrapper around the JSON GUID database with convenience methods."""

    def __init__(self, path):
        """:param path: JSON file of one game (e.g. ``guid_database_anno1800.json``)."""
        self.path = path
        #: dict[str, dict] – GUID -> {"comment": str, "locations": list[str]}
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
        """Load the JSON file (any format version). Returns {} if missing or unreadable."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {str(guid): _normalize_entry(value) for guid, value in raw.items()}
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

        * New GUID       -> created with ``[location]`` and empty comment; returns True.
        * Existing GUID  -> ``location`` appended if not yet listed; returns False.

        The return value lets callers count how many *new* GUIDs were added.
        """
        if guid not in self.entries:
            self.entries[guid] = _new_entry([location])
            return True
        locations = self.entries[guid]["locations"]
        if location not in locations:
            locations.append(location)
        return False

    def set_comment(self, guid, comment):
        """Set the comment of an EXISTING GUID (unknown GUIDs are ignored).

        :returns: True if the stored comment actually changed.
        """
        entry = self.entries.get(guid)
        if entry is None or entry["comment"] == comment:
            return False
        entry["comment"] = comment
        return True

    def set_comment_if_empty(self, guid, comment):
        """Set the comment of an EXISTING GUID only if it has no comment yet.

        Used for fallback names (<Name> / texts) so they never overwrite a
        comment that was stored before (e.g. from a "GUID - comment" line).

        :returns: True if the comment was set.
        """
        entry = self.entries.get(guid)
        if entry is None or entry["comment"] or not comment:
            return False
        entry["comment"] = comment
        return True

    def move_to(self, guids, target):
        """Move ``guids`` (with locations and comment) into the database ``target``.

        * GUID not yet in ``target`` -> copied completely.
        * GUID already in ``target`` -> location lists are merged (no duplicates);
          the target's comment is kept, the source comment is only used if the
          target has none. So no information of either database is lost.
        * Afterwards the GUIDs are removed from THIS database.

        Unknown GUIDs are ignored. Neither database is saved here – the caller
        must call :meth:`save` on both.

        :returns: tuple ``(moved, merged)`` – number of GUIDs newly created in
                  ``target`` and number of GUIDs merged into existing entries.
        """
        moved = merged = 0
        for guid in guids:
            entry = self.entries.pop(guid, None)
            if entry is None:
                continue
            if guid in target.entries:
                merged += 1
            else:
                moved += 1
            for location in entry["locations"]:
                target.add_location(guid, location)
            if entry["comment"] and not target.entries[guid]["comment"]:
                target.entries[guid]["comment"] = entry["comment"]
        return moved, merged

    def delete(self, guids):
        """Remove all given GUIDs from the database (unknown GUIDs are ignored)."""
        for guid in guids:
            self.entries.pop(guid, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def sorted_items(self):
        """Return ``[(guid, comment, [locations...]), ...]`` sorted by GUID (numeric first)."""
        return [
            (g, self.entries[g]["comment"], self.entries[g]["locations"])
            for g in sorted(self.entries, key=guid_sort_key)
        ]

    def count_free(self, ranges, from_guid):
        """Number of unregistered GUIDs inside ``ranges`` that are >= ``from_guid``.

        :param ranges:    sorted list of (start, end) tuples (own ranges of a game)
        :param from_guid: only GUIDs from this value upwards are counted

        Computed per range as "size minus used GUIDs", so it is fast even for
        huge ranges (no iteration over the ranges themselves).
        """
        used = [int(g) for g in self.entries if g.isdigit()]
        free = 0
        for start, end in ranges:
            start = max(start, from_guid)
            if start > end:
                continue
            free += (end - start + 1) - sum(1 for g in used if start <= g <= end)
        return free

    def allocate(self, count, ranges, from_guid):
        """Return ``count`` free GUIDs (as strings), ascending from ``from_guid``.

        The ranges are walked in ascending order; when one range is used up,
        allocation continues at the start of the next one. GUIDs already in
        the database are skipped, so gaps are filled first. The caller must
        ensure enough free GUIDs exist (see :meth:`count_free`).
        """
        result = []
        for start, end in ranges:
            current = max(start, from_guid)
            while current <= end and len(result) < count:
                if str(current) not in self.entries:
                    result.append(str(current))
                current += 1
            if len(result) >= count:
                break
        return result


def migrate_legacy_database(target_game):
    """Move the old single ``guid_database.json`` into the database of ``target_game``.

    Older versions of the tool only knew ONE database. On the first start of
    the multi-game version this file is copied to the database file of
    ``target_game`` (Anno 1800 by default) and the old file is renamed to
    ``guid_database.json.bak`` so the migration runs only once.

    Nothing happens if there is no legacy file or if the target database
    already exists (an existing database is never overwritten).

    :returns: True if a migration was performed, otherwise False.
    """
    target = GAMES[target_game]["db_file"]
    if not os.path.exists(LEGACY_DB_FILE) or os.path.exists(target):
        return False
    try:
        shutil.copy2(LEGACY_DB_FILE, target)
        os.replace(LEGACY_DB_FILE, LEGACY_DB_FILE + ".bak")
        return True
    except Exception as e:
        print(f"Error migrating legacy database: {e}")
        return False
