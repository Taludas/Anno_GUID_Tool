"""
collisions.py
=============

Detection of GUID collisions.

A GUID is "defined" by a mod if it appears in a ``<GUID>`` / ``<LineId>``
tag of one of its XML files. The mod of a file is the folder directly above
``data/`` (see :func:`core.xml_scanner.mod_of_location`).

Three kinds of collision are detected:

* **other mod** – the GUID is defined in more than one mod.
* **duplicate** – ONE mod defines the GUID more than once: in two asset
  definitions (``<Standard>`` blocks, same or different files) or twice in
  the same texts_*.xml file. An asset plus its own text entry (same GUID,
  the normal Anno way) is not a duplicate.
* **reserved elsewhere** – the GUID is reserved in a "Free GUIDs" list of
  ANOTHER mod project. The list selected in the Free GUIDs tab counts as the
  mod's own project if it holds any of the mod's GUIDs; otherwise the list
  with most of them (see :func:`own_project_lists`).

Two uses:

* :func:`find_import_collisions` – while a mod is imported (tab "GUID
  Database", collision dialog).
* :func:`scan_folder_collisions` – scan a folder with many mods (folders
  and ZIPs) WITHOUT importing anything, e.g. to check other modders' work.

No Tkinter here.
"""

import os
from collections import Counter
from dataclasses import dataclass, field

from core.xml_scanner import mod_of_location, scan_mod


def mods_of_locations(locations):
    """Set of known mods of a list of locations (unknown mods left out)."""
    return {m for m in map(mod_of_location, locations) if m}


def guids_by_mod(guid_files):
    """``{mod: {guids}}`` from ``{guid: {locations}}``."""
    result = {}
    for guid, locations in guid_files.items():
        for mod in mods_of_locations(locations):
            result.setdefault(mod, set()).add(guid)
    return result


def own_project_lists(guid_files, reservations):
    """Find the Free GUIDs list (mod project) that each imported mod belongs to.

    1. The ACTIVE list (selected in the Free GUIDs tab), if it holds any of
       the mod's GUIDs – the user normally imports a mod while its project
       is selected.
    2. Otherwise the list that holds MOST of the mod's reserved GUIDs
       (tie: alphabetically first).

    Mods without any reserved GUID have no own list.

    :return: ``{mod: list name}``
    """
    list_of = {g: name for name, items in reservations.lists.items() for g in items}
    result = {}
    for mod, guids in guids_by_mod(guid_files).items():
        counts = Counter(list_of[g] for g in guids if g in list_of)
        if reservations.active in counts:
            result[mod] = reservations.active
        elif counts:
            result[mod] = min(counts, key=lambda n: (-counts[n], n.lower()))
    return result


@dataclass
class ImportCollision:
    """One GUID of an import that collides, with all reasons.

    :ivar guid:        the colliding GUID
    :ivar comment:     comment of the GUID in the database (may be "")
    :ivar offenders:   mods of THIS import that would get a new GUID on
                       "migrate" (always at least one)
    :ivar owner_mods:  OTHER mods that define the GUID ("other mod")
    :ivar duplicates:  ``{mod: [files]}`` – mods of this import that define
                       the GUID more than once ("duplicate")
    :ivar reserved_in: Free GUIDs lists of other projects that reserve the
                       GUID ("reserved elsewhere")
    :ivar own_list:    the Free GUIDs list assumed to be the mod's own project
                       (shown in the dialog), or ""
    """
    guid: str
    comment: str = ""
    offenders: list = field(default_factory=list)
    owner_mods: list = field(default_factory=list)
    duplicates: dict = field(default_factory=dict)
    reserved_in: list = field(default_factory=list)
    own_list: str = ""

    @property
    def can_migrate(self):
        """Migrating is impossible for duplicates: the tool cannot tell which
        of the definitions (and which references) should get the new GUID."""
        return not self.duplicates


def find_import_collisions(guid_files, db, duplicates=None, reservations=None):
    """Return the collisions an import of ``guid_files`` would create.

    :param guid_files:   ``{guid: {locations}}`` of the mod(s) being imported
                         (from :func:`scan_mod`)
    :param db:           :class:`GuidDatabase` of the active game
    :param duplicates:   ``{guid: {mod: [files]}}`` from :func:`scan_mod`
    :param reservations: :class:`GuidReservations` of the active game

    Not reported again:

    * re-importing a mod that is already in the database,
    * other-mod collisions accepted for exactly these mods (``accepted_mods``),
    * duplicates already recorded for the mod (``duplicate_in``),
    * reservations of a list the user already accepted (``reserved_in``).

    :return: list of :class:`ImportCollision`, sorted by GUID
    """
    found = {}

    def get(guid):
        if guid not in found:
            comment = db.entries[guid]["comment"] if guid in db else ""
            found[guid] = ImportCollision(guid, comment)
        return found[guid]

    # 1. Defined in another mod.
    for guid, locations in guid_files.items():
        new_mods = mods_of_locations(locations)
        old_mods = db.mods_of(guid)
        all_mods = new_mods | old_mods
        if len(all_mods) < 2 or all_mods <= db.accepted_mods(guid):
            continue
        owners = old_mods or {min(new_mods)}
        offenders = new_mods - owners
        if offenders:
            c = get(guid)
            c.owner_mods = sorted(owners)
            c.offenders = sorted(set(c.offenders) | offenders)

    # 2. Defined more than once inside one mod.
    for guid, per_mod in (duplicates or {}).items():
        if guid not in guid_files:
            continue
        for mod, files in per_mod.items():
            if mod in db.duplicate_in(guid):
                continue
            c = get(guid)
            c.duplicates[mod] = files
            c.offenders = sorted(set(c.offenders) | {mod})

    # 3. Reserved in the Free GUIDs list of another project.
    if reservations is not None:
        own_lists = own_project_lists(guid_files, reservations)
        list_of = {g: name for name, items in reservations.lists.items() for g in items}
        accepted = {g: set(db.entries[g].get("reserved_in", [])) for g in guid_files if g in db}
        for mod, guids in guids_by_mod(guid_files).items():
            for guid in guids:
                name = list_of.get(guid)
                if name is None or name == own_lists.get(mod) or name in accepted.get(guid, ()):
                    continue
                c = get(guid)
                c.reserved_in = sorted(set(c.reserved_in) | {name})
                c.own_list = own_lists.get(mod, "")
                c.offenders = sorted(set(c.offenders) | {mod})

    return [found[g] for g in sorted(found, key=lambda g: (len(g), g))]


@dataclass
class FolderScanResult:
    """Result of :func:`scan_folder_collisions`.

    :ivar mods:       names of all mods found
    :ivar xml_count:  number of XML files scanned
    :ivar guid_count: number of different GUIDs found
    :ivar between:    ``{guid: [mods]}`` – GUIDs defined in more than one
                      of the scanned mods
    :ivar duplicates: ``{guid: {mod: [files]}}`` – GUIDs that one scanned
                      mod defines more than once
    :ivar with_db:    ``{guid: [database mods]}`` – GUIDs of the scanned mods
                      that the database lists for OTHER mods
    :ivar reserved:   ``{guid: [list names]}`` – GUIDs of the scanned mods that
                      are reserved in your Free GUIDs lists
    :ivar errors:     ``[(path, message)]`` – archives that could not be read
    """
    mods: set = field(default_factory=set)
    xml_count: int = 0
    guid_count: int = 0
    between: dict = field(default_factory=dict)
    duplicates: dict = field(default_factory=dict)
    with_db: dict = field(default_factory=dict)
    reserved: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)

    @property
    def colliding_guids(self):
        """All GUIDs with at least one kind of collision."""
        return set(self.between) | set(self.duplicates) | set(self.with_db) | set(self.reserved)


def _mod_paths(folder):
    """The folder itself plus every ``.zip`` file below it."""
    paths = [folder]
    for root, _, files in os.walk(folder):
        paths += [os.path.join(root, n) for n in sorted(files) if n.lower().endswith(".zip")]
    return paths


def scan_folder_collisions(folder, db, reservations=None, predicate=str.isdigit):
    """Scan all mods in ``folder`` (sub folders and ZIPs) for GUID collisions.

    Nothing is written to the database or the reservations.

    :param folder:       folder that contains the mods (any depth)
    :param db:           :class:`GuidDatabase` to compare with
    :param reservations: :class:`GuidReservations` to compare with (optional)
    :param predicate:    which GUIDs to check (default: every numeric GUID,
                         not only the own ranges, so other modders' work can
                         be checked too)
    :return: :class:`FolderScanResult`
    """
    result = FolderScanResult()
    guid_mods = {}   # guid -> set of mods
    for path in _mod_paths(folder):
        try:
            guid_files, _, _, xml_count, duplicates = scan_mod(path, predicate)
        except Exception as e:  # e.g. corrupt ZIP
            result.errors.append((path, str(e)))
            continue
        result.xml_count += xml_count
        for guid, locations in guid_files.items():
            mods = mods_of_locations(locations)
            result.mods |= mods
            guid_mods.setdefault(guid, set()).update(mods)
        for guid, per_mod in duplicates.items():
            for mod, files in per_mod.items():
                result.duplicates.setdefault(guid, {}).setdefault(mod, []).extend(files)

    list_of = {}
    if reservations is not None:
        for name, items in reservations.lists.items():
            for guid in items:
                list_of.setdefault(guid, []).append(name)

    result.guid_count = len(guid_mods)
    for guid, mods in guid_mods.items():
        if len(mods) > 1:
            result.between[guid] = sorted(mods)
        others = db.mods_of(guid) - mods
        if others:
            result.with_db[guid] = sorted(others)
        if guid in list_of:
            result.reserved[guid] = sorted(list_of[guid])
    return result
