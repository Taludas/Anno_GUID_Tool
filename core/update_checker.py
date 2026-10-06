"""
update_checker.py
=================

Checks on GitHub whether a newer version of the tool is available.

How it works
------------
1. The ``version.txt`` of the ``main`` branch is downloaded from GitHub
   (raw file URL, see ``VERSION_URL``). The normal GitHub page
   (``.../blob/main/version.txt``) returns HTML, so the raw URL is used.
2. The remote version is compared with the local version (``app.version``).
3. Only if the remote version is NEWER, the caller shows the update popup.

The check runs in a background thread so a slow or missing internet
connection never blocks the UI. Every error (offline, proxy, timeout,
invalid content) is ignored silently – the update check must never
disturb the normal use of the tool.

This module contains no UI code; the popup is in ``dialogs/update_dialog.py``.
"""

import re
import threading
import urllib.request

#: GitHub project page (opened from the update popup).
GITHUB_REPO_URL = "https://github.com/gz2k2/Anno_GUID_Tool"

#: Ko-fi page of the author (opened from the "Ko-Fi Sponsor" button).
KOFI_URL = "https://ko-fi.com/gz2k2"

#: Raw content of version.txt on the main branch (plain text, e.g. "v1.23.45").
VERSION_URL = "https://raw.githubusercontent.com/gz2k2/Anno_GUID_Tool/main/version.txt"

#: Maximum time (seconds) for the HTTP request.
REQUEST_TIMEOUT = 5

#: "v1.23.45", "1.23", "v0.20.5-beta" -> group 1 = "1.23.45", group 2 = "beta"
_VERSION_PATTERN = re.compile(r"v?(\d+(?:\.\d+)*)(?:[-+ ]?([0-9A-Za-z.]+))?", re.IGNORECASE)


def parse_version(text):
    """Convert a version string into a comparable tuple.

    Result: ``((major, minor, patch, ...), is_final_release)``

    * Missing parts count as 0 -> "1.2" == "1.2.0".
    * A suffix such as "-beta" marks a pre-release, which is OLDER than the
      final release with the same numbers ("1.2.0-beta" < "1.2.0").
    * Returns None if the text contains no version number.
    """
    match = _VERSION_PATTERN.search((text or "").strip())
    if not match:
        return None
    numbers = [int(part) for part in match.group(1).split(".")]
    while len(numbers) > 1 and numbers[-1] == 0:  # "1.2.0" -> (1, 2)
        numbers.pop()
    return tuple(numbers), match.group(2) is None


def is_newer(remote, local):
    """True if version string ``remote`` is newer than ``local``.

    If one of them cannot be parsed, False is returned (no false alarm).
    """
    remote_v, local_v = parse_version(remote), parse_version(local)
    if remote_v is None or local_v is None:
        return False
    return remote_v > local_v


def fetch_remote_version():
    """Download the version string from GitHub (first non-empty line).

    Raises an exception on any network or decoding problem.
    """
    request = urllib.request.Request(
        VERSION_URL,
        headers={"User-Agent": "Anno-GUID-Tool-Update-Check", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        text = response.read().decode("utf-8-sig", errors="ignore")
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_for_update_async(local_version, on_update_available):
    """Start the update check in a background thread.

    :param local_version:       version of the running program (e.g. "v1.23.45")
    :param on_update_available: callable ``(remote_version)``; called from the
                                BACKGROUND THREAD and only if a newer version
                                exists. Tkinter is not thread-safe, so the
                                callback must hand the work over to the UI
                                thread (see ``GUIDManagerApp._start_update_check``).

    Without a local version (version.txt missing) no check is done, because
    every remote version would look "newer".
    """
    if not local_version:
        return

    def worker():
        try:
            remote = fetch_remote_version()
            if is_newer(remote, local_version):
                on_update_available(remote)
        except Exception as e:  # offline, proxy, timeout, ... -> ignore
            print(f"Update check failed: {e}")

    # daemon=True: the thread never keeps the program alive on exit.
    threading.Thread(target=worker, name="UpdateCheck", daemon=True).start()
