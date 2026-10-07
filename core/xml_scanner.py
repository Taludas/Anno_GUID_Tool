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

import html
import os
import shutil
import tempfile
import zipfile

from core.constants import (
    COMMENT_LINE_PATTERN,
    DEFAULT_COMMENT_LANGUAGE,
    GUID_TAG_PATTERN,
    NUMBER_PATTERN,
    STANDARD_BLOCK_PATTERN,
    STANDARD_GUID_PATTERN,
    STANDARD_NAME_PATTERN,
    TEXT_ID_FIRST_PATTERN,
    TEXT_TEXT_FIRST_PATTERN,
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


def _clean_text(value):
    """Trim, collapse inner whitespace/line breaks and decode XML entities (&amp; -> &)."""
    return " ".join(html.unescape(value).split())


def is_texts_file(rel_path):
    """True if the file name matches texts_*.xml (localisation file)."""
    return bool(TEXTS_FILE_PATTERN.match(os.path.basename(rel_path.replace("\\", "/"))))


def extract_asset_names(content):
    """Return ``{guid: name}`` from the ``<Standard>`` blocks of asset XMLs.

    Same structure in Anno 117 and Anno 1800::

        <Standard>
          <GUID>2144000003</GUID>
          <Name>Praefectus Adriana</Name>

    Blocks without GUID or without (non-empty) Name are ignored. If a GUID
    appears in several blocks, the FIRST name wins.
    """
    names = {}
    for block in STANDARD_BLOCK_PATTERN.findall(content):
        guid = STANDARD_GUID_PATTERN.search(block)
        name = STANDARD_NAME_PATTERN.search(block)
        if guid and name:
            text = _clean_text(name.group(1))
            if text:
                names.setdefault(guid.group(1), text)
    return names


def extract_text_names(content):
    """Return ``{guid: text}`` from the text entries of a texts_*.xml file.

    Both layouts are supported:

    * Anno 1800 – ID first:   ``<Text><GUID>…</GUID><Text>…</Text></Text>``
    * Anno 117  – text first: ``<Text><Text>…</Text><LineId>…</LineId></Text>``

    ``<GUID>`` and ``<LineId>`` are accepted in both layouts. XML comments
    are removed first so commented-out entries are not used.
    """
    content = XML_COMMENT_PATTERN.sub("", content)
    names = {}
    for _, guid, text in TEXT_ID_FIRST_PATTERN.findall(content):
        text = _clean_text(text)
        if text:
            names.setdefault(guid, text)
    for text, _, guid in TEXT_TEXT_FIRST_PATTERN.findall(content):
        text = _clean_text(text)
        if text:
            names.setdefault(guid, text)
    return names


def text_file_language(rel_path):
    """Language part of a texts file name: "…/texts_german.xml" -> "german"."""
    name = os.path.basename(rel_path.replace("\\", "/")).lower()
    return name[len("texts_"):-len(".xml")]


def _text_file_rank(rel_path, language):
    """Sort key for texts_*.xml files.

    Order: 0 = configured language, 1 = English (fallback), 2 = all others.
    Files of the same rank are sorted by path so the result is stable.
    """
    file_lang = text_file_language(rel_path)
    if file_lang == language:
        rank = 0
    elif file_lang == DEFAULT_COMMENT_LANGUAGE:
        rank = 1
    else:
        rank = 2
    return (rank, rel_path.lower())


def normalize_file_path(raw_path):
    """Normalise a mod-relative file path for display / database storage.

    * Backslashes are converted to forward slashes.
    * Keeps only ONE folder level above '/data/' (e.g. '[ModName]/data/base/...').
    * Localisation files (``texts_german.xml``, ``texts_english.xml`` …) are
      collapsed into ``texts_*.xml`` so a LineId shows up only once instead
      of once per language.
    """
    normalized = raw_path.replace("\\", "/")
    
    parts = [p for p in normalized.split("/") if p]
    if "data" in parts:
        data_index = parts.index("data")
        if data_index > 0:
            normalized = "/".join(parts[data_index - 1:])

    directory, filename = os.path.split(normalized)
    if TEXTS_FILE_PATTERN.match(filename):
        filename = "texts_*.xml"
    return f"{directory}/{filename}" if directory else filename


def mod_folder_prefix(path):
    """Name of the selected mod folder, used as first part of every location.

    Example: selected folder ``C:/Mods/[Specialists] super-specialists [gz2k2]``
    -> ``"[Specialists] super-specialists [gz2k2]"``, so the location becomes
    ``[Specialists] super-specialists [gz2k2]/data/base/...`` instead of
    ``data/base/...``. That way the database shows which mod a GUID belongs to.

    ZIP archives return "" – their entry names are used unchanged (a ZIP
    usually already contains the mod folder as top-level entry).
    """
    if is_zip_path(path) or not os.path.isdir(path):
        return ""
    return os.path.basename(os.path.normpath(path))


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


def scan_mod(path, predicate, language=DEFAULT_COMMENT_LANGUAGE):
    """Scan all XML files once and collect GUIDs, their files, comments and names.

    :param path:      mod folder or ZIP archive
    :param predicate: callable ``(guid_str) -> bool`` deciding which GUIDs to keep
    :param language:  language of the texts_*.xml file to read names from,
                      e.g. "german" -> texts_german.xml ("Language Comment"
                      setting). Fallback: texts_english.xml, then any other.
    :returns: tuple ``(guid_files, comments, names, xml_count)``

              * ``guid_files``: ``{guid: {normalised file paths}}`` for every
                GUID defined in a <GUID>/<LineId> tag that passes ``predicate``.
              * ``comments``: ``{guid: comment}`` for ALL "GUID - comment"
                lines found in XML comments of ANY file of the mod (the
                comment may live in a different file than the definition).
                Not filtered by ``predicate`` so the caller can report
                comments whose GUID was not registered. First comment wins.
              * ``names``: ``{guid: name}`` fallback names, used when a GUID
                has no comment. Priority:
                  1. ``<Name>`` of the asset (``<Standard>`` block, any XML)
                  2. ``<Text>`` of the entry in a texts_*.xml file, searched
                     per GUID in this order: texts_<language>.xml ->
                     texts_english.xml -> any other language file
              * ``xml_count``: number of XML files scanned
    """
    prefix = mod_folder_prefix(path)   # "" for ZIP archives
    guid_files = {}
    all_comments = {}
    asset_names = {}
    text_names_per_file = []   # [(rel_path, {guid: text}), ...]
    xml_count = 0
    for rel_path, content in iter_xml_files(path):
        xml_count += 1
        full_rel = os.path.join(prefix, rel_path) if prefix else rel_path
        norm_path = normalize_file_path(full_rel)
        for guid in extract_guids_from_text(content):
            if predicate(guid):
                guid_files.setdefault(guid, set()).add(norm_path)
        for guid, text in extract_comments_from_text(content).items():
            all_comments.setdefault(guid, text)

        if is_texts_file(rel_path):
            text_names_per_file.append((rel_path, extract_text_names(content)))
        else:
            for guid, name in extract_asset_names(content).items():
                asset_names.setdefault(guid, name)

    # Build the fallback names: asset <Name> first, then texts in language
    # order (configured -> English -> others). setdefault keeps the first
    # hit, so a GUID missing in texts_<language>.xml falls back to English.
    # Only GUIDs that were actually collected are kept.
    language = (language or DEFAULT_COMMENT_LANGUAGE).strip().lower()
    names = {g: n for g, n in asset_names.items() if g in guid_files}
    for _, file_names in sorted(text_names_per_file,
                                key=lambda item: _text_file_rank(item[0], language)):
        for guid, text in file_names.items():
            if guid in guid_files:
                names.setdefault(guid, text)

    return guid_files, all_comments, names, xml_count


def collect_guids(path, predicate):
    """Scan all XML files and collect GUIDs matching ``predicate``.

    :param path:      mod folder or ZIP archive
    :param predicate: callable ``(guid_str) -> bool`` deciding which GUIDs to keep
                      (e.g. ``app.game.is_dummy_guid``)
    :returns: tuple ``(guid_files, xml_count)`` where ``guid_files`` maps each
              matching GUID to a set of normalised file paths it was found in,
              and ``xml_count`` is the number of XML files scanned.
    """
    guid_files, _, _, xml_count = scan_mod(path, predicate)
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
                    