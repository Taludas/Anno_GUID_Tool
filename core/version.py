"""
version.py
==========

Reads the program version from ``version.txt`` (see ``VERSION_FILE`` in
constants.py) – inside the
PyInstaller bundle or in the program folder. The file contains only the version string, e.g.::

    v1.23.45

The version is shown in the window title. If the file is missing, empty
or unreadable, an empty string is returned and the title is shown without
version – the program never fails because of this file.
"""

from core.constants import VERSION_FILES


def read_version(paths=None):
    """Return the version string from the first readable file in ``paths``.

    :param paths: list of candidate files; defaults to ``VERSION_FILES``
                  (PyInstaller bundle first, then the program folder).
    """
    for path in paths or VERSION_FILES:
        version = _read_first_line(path)
        if version:
            return version
    return ""


def _read_first_line(path):
    """Return the first non-empty, trimmed line of ``path`` ("" on any error).

    ``utf-8-sig`` removes a BOM that some Windows editors (e.g. Notepad)
    write at the start of the file; otherwise it would appear in the title.
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line:
                    return line
    except OSError:
        pass
    return ""
