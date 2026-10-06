"""
main.py
=======

Entry point of the Anno GUID Tool.

Start with:  python main.py

``config.ini`` and the per-game databases ``guid_database_anno117.json`` /
``guid_database_anno1800.json`` are read from / written to the current
working directory. An old single ``guid_database.json`` is migrated to the
Anno 1800 database automatically on first start.

Project layout
--------------
main.py                  – this file, starts the application
version.txt              – program version shown in the title (e.g. v1.23.45)
app.py                   – main window, game selector, shared state, tab wiring, translation
core/constants.py        – program name/author, file names, default ranges, regex patterns
core/version.py          – reads the program version from version.txt
core/translations.py     – all UI texts (German / English)
core/config_manager.py   – config.ini handling, per-game GUID range lists (GameProfile)
core/guid_database.py    – per-game JSON database, free GUID allocation, legacy migration
core/xml_scanner.py      – reading / rewriting XML files in folders and ZIPs
core/update_checker.py   – compares the own version with version.txt on GitHub
tabs/database_tab.py     – tab "GUID Database"
tabs/replace_tab.py      – tab "Replace Dummy GUIDs"
tabs/settings_tab.py     – tab "Settings" (sub tabs General / Anno 117 / Anno 1800)
dialogs/update_dialog.py – popup "new version available" with link to GitHub
"""

import os
import sys

# Make "core", "tabs" and "dialogs" importable regardless of the directory the script
# is started from (e.g. double-click, IDE run configuration).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import GUIDManagerApp  # noqa: E402  (import after sys.path tweak)


def main():
    """Create the main window and run the Tk event loop."""
    app = GUIDManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
