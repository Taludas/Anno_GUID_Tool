"""
guid_reservations.py
====================

Temporarily reserved GUIDs of the tab "Free GUIDs".

While a mod is being written, the user lets the tool suggest a continuous
block of free GUIDs and copies them into the mod one by one. These GUIDs are
not in the database yet (they are only registered when the finished mod is
imported), so they are kept here to make sure they are never suggested or
assigned a second time.

Reserved GUIDs are grouped in named LISTS, one per mod project, so several
mods can be worked on at the same time. Every game has its OWN reservation
file, e.g. ``guid_reservations_anno1800.json``::

    {
        "active": "Specialists",
        "lists": {
            "Specialists": {
                "2144009900": {"used": true, "comment": "Praefectus Name"},
                "2144009901": {"used": false}
            },
            "New Ships": {
                "2144009950": {"used": false}
            }
        }
    }

``comment`` is the user's planning comment (only written when not empty).
When the finished mod is registered, the comment found in the mod replaces
it; if the mod has none, the planning comment is taken over into the
database.

``active`` is the list shown in the tab. All methods that read or change
GUIDs work on the active list, except :meth:`taken`, which returns the GUIDs
of ALL lists – a GUID reserved for one project is blocked for every other
project as well.

An older file without lists (``{"<guid>": {"used": ...}, ...}``) is loaded
as one list named :data:`LEGACY_LIST_NAME`.

State of a reserved GUID
------------------------
* **free**       – suggested, not used yet (``used`` false)
* **used**       – the user marked it as used in a mod (``used`` true)
* **registered** – the GUID is now in the game's database (mod imported).
  This is not stored here; the tab derives it from the database.

Both free and used GUIDs block allocation. Free GUIDs are released with
"Clean Up"; used GUIDs stay reserved until they are registered or removed
by the user.
"""

import json
import os

from core.guid_database import guid_sort_key

#: Name of the list that GUIDs of an old single-list file are moved into.
LEGACY_LIST_NAME = "Default"


def _clean_item(value):
    """Convert one reserved GUID read from JSON into ``{"used": bool[, "comment": str]}``."""
    if not isinstance(value, dict):
        return {"used": False}
    item = {"used": bool(value.get("used"))}
    comment = str(value.get("comment") or "").strip()
    if comment:
        item["comment"] = comment
    return item


def _clean_list(raw):
    """Convert one list read from JSON into ``{guid: {"used": bool, ...}}``."""
    if not isinstance(raw, dict):
        return {}
    return {str(guid): _clean_item(value) for guid, value in raw.items()}


class GuidReservations:
    """Wrapper around the JSON reservation file of one game."""

    def __init__(self, path):
        """:param path: JSON file of one game (e.g. ``guid_reservations_anno1800.json``)."""
        self.path = path
        #: dict[str, dict[str, dict]] – list name -> GUID -> {"used": bool}
        self.lists = {}
        #: name of the active list, or None if there is no list
        self.active = None
        self._load()

    # ------------------------------------------------------------------
    # Active list (Python protocol helpers work on it)
    # ------------------------------------------------------------------
    @property
    def entries(self):
        """``{guid: {"used": bool}}`` of the active list (empty dict if none)."""
        return self.lists.get(self.active, {})

    def __contains__(self, guid):
        return guid in self.entries

    def __len__(self):
        return len(self.entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self):
        """Load the JSON file. Missing or unreadable file -> no lists."""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"Error loading GUID reservations: {e}")
            return
        if isinstance(raw.get("lists"), dict):
            self.lists = {str(name): _clean_list(items) for name, items in raw["lists"].items()}
            active = raw.get("active")
        else:  # old single-list file
            self.lists = {LEGACY_LIST_NAME: _clean_list(raw)} if raw else {}
            active = LEGACY_LIST_NAME
        self.active = active if active in self.lists else next(iter(self.list_names()), None)

    def save(self):
        """Write all lists to disk (GUIDs sorted, pretty-printed)."""
        data = {
            "active": self.active,
            "lists": {
                name: {g: items[g] for g in sorted(items, key=guid_sort_key)}
                for name, items in self.lists.items()
            },
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Lists
    # ------------------------------------------------------------------
    def list_names(self):
        """Names of all lists, sorted alphabetically (case-insensitive)."""
        return sorted(self.lists, key=str.lower)

    def add_list(self, name):
        """Create an empty list ``name`` and make it active (no-op if it exists)."""
        self.lists.setdefault(name, {})
        self.active = name

    def rename_list(self, old, new):
        """Rename list ``old`` to ``new`` (keeps its GUIDs and the active state)."""
        if old not in self.lists or new in self.lists:
            return
        self.lists[new] = self.lists.pop(old)
        if self.active == old:
            self.active = new

    def delete_list(self, name):
        """Delete list ``name`` (its GUIDs are released); another list becomes active."""
        self.lists.pop(name, None)
        if self.active == name:
            self.active = next(iter(self.list_names()), None)

    def set_active(self, name):
        """Make list ``name`` the active one (unknown names are ignored)."""
        if name in self.lists:
            self.active = name

    # ------------------------------------------------------------------
    # GUIDs of the active list
    # ------------------------------------------------------------------
    def add(self, guids):
        """Reserve ``guids`` as free in the active list (existing GUIDs keep their state)."""
        if self.active is None:
            return
        items = self.lists[self.active]
        for guid in guids:
            items.setdefault(guid, {"used": False})

    def set_used(self, guid, used):
        """Mark a GUID of the active list as used / not used (unknown GUIDs are ignored)."""
        if guid in self.entries:
            self.entries[guid]["used"] = bool(used)

    def set_comment(self, guid, comment):
        """Set the planning comment of a GUID of the active list ("" removes it)."""
        item = self.entries.get(guid)
        if item is None:
            return
        comment = comment.strip()
        if comment:
            item["comment"] = comment
        else:
            item.pop("comment", None)

    def comment(self, guid):
        """Planning comment of ``guid`` in the active list ("" if none)."""
        return self.entries.get(guid, {}).get("comment", "")

    def remove(self, guids):
        """Remove ``guids`` from the active list (unknown GUIDs are ignored)."""
        for guid in guids:
            self.entries.pop(guid, None)

    def is_used(self, guid):
        """True if ``guid`` is in the active list AND marked as used."""
        return self.entries.get(guid, {}).get("used", False)

    def sorted_guids(self):
        """All GUIDs of the active list, sorted numerically."""
        return sorted(self.entries, key=guid_sort_key)

    def last_guid(self):
        """Highest numeric GUID of the active list as int, or None if it is empty."""
        numbers = [int(g) for g in self.entries if g.isdigit()]
        return max(numbers) if numbers else None

    # ------------------------------------------------------------------
    # All lists
    # ------------------------------------------------------------------
    def taken(self):
        """GUIDs reserved in ANY list – must not be suggested or assigned again."""
        return {guid for items in self.lists.values() for guid in items}

    def planning_comments(self):
        """``{guid: comment}`` of the planning comments in ALL lists."""
        return {guid: item["comment"] for items in self.lists.values()
                for guid, item in items.items() if item.get("comment")}
