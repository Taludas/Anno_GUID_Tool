"""
xml_scanner.py
==============

File-system helpers for reading and rewriting the XML files of a mod.

A "mod path" can be either

* a **folder** – all ``*.xml`` files are searched recursively, or
* a **ZIP archive** – all ``*.xml`` entries inside the archive are used.

All functions here are UI-independent (no Tkinter), so they can be reused
or unit-tested on their own.
"""

import os
import shutil
import tempfile
import zipfile

from core.constants import (
    COMMENT_LINE_PATTERN,
    GUID_TAG_PATTERN,
    NUMBER_PATTERN,
    TEXTS_FILE_PATTERN,
    XML_COMMENT_PATTERN,
)


def is_zip_path(path):
    """True if ``path`` is an existing file with a ``.zip`` extension."""
    return os.path.isfile(path) and path.lower().endswith(".zip")


def extract_guids_from_text(content):
    """Return the set of all GUID / LineId values *defined* in an XML text.

    Only values inside ``<GUID>`` and ``<LineId>`` tags are returned –
    references in other tags (e.g. ``<Product>``) are intentionally ignored.
    """
    return set(GUID_TAG_PATTERN.findall(content))


def extract_comments_from_text(content):
    """Return ``{guid: comment}`` for all "GUID - comment" lines inside XML comments.

    Only text inside ``<!-- ... -->`` is searched, so normal XML content is
    never mistaken for a comment. Example::

        <!--
        2144009900 - Praefectus Specialists Name
        2144009901 - Praefectus Specialists Description
        -->

    -> ``{"2144009900": "Praefectus Specialists Name",
          "2144009901": "Praefectus Specialists Description"}``

    If the same GUID is commented several times in one text, the FIRST
    comment wins.
    """
    comments = {}
    for block in XML_COMMENT_PATTERN.findall(content):
        for guid, text in COMMENT_LINE_PATTERN.findall(block):
            text = text.strip()
            if text:
                comments.setdefault(guid, text)
    return comments


def normalize_file_path(raw_path):
    """Normalise a mod-relative file path for display / database storage.

    * Backslashes are converted to forward slashes.
    * Localisation files (``texts_german.xml``, ``texts_english.xml`` …) are
      collapsed into ``texts_*.xml`` so a LineId shows up only once instead
      of once per language.
    """
    normalized = raw_path.replace("\\", "/")
    directory, filename = os.path.split(normalized)
    if TEXTS_FILE_PATTERN.match(filename):
        filename = "texts_*.xml"
    return f"{directory}/{filename}" if directory else filename


def iter_xml_files(path):
    """Yield ``(relative_path, content)`` for every XML file of a mod.

    * ZIP: ``relative_path`` is the entry name inside the archive. Errors
      while opening the archive are raised to the caller (so the UI can
      show a message box).
    * Folder: ``relative_path`` is relative to ``path``. Unreadable single
      files are skipped with a console message so one bad file does not
      abort the whole scan.

    Content is decoded as UTF-8; invalid bytes are ignored.
    """
    if is_zip_path(path):
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                if info.filename.lower().endswith(".xml"):
                    with zf.open(info) as f:
                        yield info.filename, f.read().decode("utf-8", errors="ignore")

    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for name in files:
                if not name.lower().endswith(".xml"):
                    continue
                full_path = os.path.join(root, name)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading file {full_path}: {e}")
                    continue
                yield os.path.relpath(full_path, path), content


def scan_mod(path, predicate):
    """Scan all XML files once and collect GUIDs, their files and their comments.

    :param path:      mod folder or ZIP archive
    :param predicate: callable ``(guid_str) -> bool`` deciding which GUIDs to keep
    :returns: tuple ``(guid_files, comments, xml_count)``

              * ``guid_files``: ``{guid: {normalised file paths}}`` for every
                GUID defined in a <GUID>/<LineId> tag that passes ``predicate``
              * ``comments``: ``{guid: comment}`` for ALL "GUID - comment"
                lines found in XML comments of ANY file of the mod (the
                comment may live in a different file than the definition).
                Not filtered by ``predicate`` so the caller can report
                comments whose GUID was not registered. First comment wins.
              * ``xml_count``: number of XML files scanned
    """
    guid_files = {}
    all_comments = {}
    xml_count = 0
    for rel_path, content in iter_xml_files(path):
        xml_count += 1
        norm_path = normalize_file_path(rel_path)
        for guid in extract_guids_from_text(content):
            if predicate(guid):
                guid_files.setdefault(guid, set()).add(norm_path)
        for guid, text in extract_comments_from_text(content).items():
            all_comments.setdefault(guid, text)

    return guid_files, all_comments, xml_count


def collect_guids(path, predicate):
    """Scan all XML files and collect GUIDs matching ``predicate``.

    :param path:      mod folder or ZIP archive
    :param predicate: callable ``(guid_str) -> bool`` deciding which GUIDs to keep
                      (e.g. ``app.game.is_dummy_guid``)
    :returns: tuple ``(guid_files, xml_count)`` where ``guid_files`` maps each
              matching GUID to a set of normalised file paths it was found in,
              and ``xml_count`` is the number of XML files scanned.
    """
    guid_files, _, xml_count = scan_mod(path, predicate)
    return guid_files, xml_count


def apply_dummy_map(content, dummy_map):
    """Replace every standalone occurrence of a dummy GUID with its real GUID.

    ``dummy_map`` maps dummy GUID strings to real GUID strings. The
    replacement is done in ONE regex pass over all numbers, so a value that
    was just replaced can never be replaced a second time (no chain effects).
    Numbers that are not in ``dummy_map`` are written back unchanged.
    """
    return NUMBER_PATTERN.sub(lambda m: dummy_map.get(m.group(1), m.group(1)), content)


def rewrite_xml_files(path, transform):
    """Apply ``transform(content) -> new_content`` to every XML file of a mod.

    * Folder: each file is rewritten in place, but only if its content
      actually changed (keeps file timestamps of untouched files).
    * ZIP: a new archive is built in a temporary directory (XML entries
      transformed, all other entries copied byte-for-byte with their original
      ZipInfo), then it replaces the original archive. The temp directory is
      always removed, even on errors.
    """
    if is_zip_path(path):
        temp_dir = tempfile.mkdtemp()
        try:
            temp_zip = os.path.join(temp_dir, "temp_mod.zip")
            with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(temp_zip, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename.lower().endswith(".xml"):
                        text = data.decode("utf-8", errors="ignore")
                        data = transform(text).encode("utf-8")
                    zout.writestr(item, data)
            shutil.move(temp_zip, path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return

    for root, _, files in os.walk(path):
        for name in files:
            if not name.lower().endswith(".xml"):
                continue
            full_path = os.path.join(root, name)
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            new_content = transform(content)
            if new_content != content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
