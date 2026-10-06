"""
main.py
=======

Entry point of the Anno GUID Tool.

Start with:  python main.py

``config.ini`` and ``guid_database.json`` are read from / written to the
current working directory (same behaviour as the former single-file version).

Project layout
--------------
main.py                  – this file, starts the application
app.py                   – main window, shared state, tab wiring, translation
core/constants.py        – file names, default ranges, regex patterns
core/translations.py     – all UI texts (German / English)
core/config_manager.py   – config.ini handling + GUID range checks
core/guid_database.py    – guid_database.json handling + free GUID allocation
core/xml_scanner.py      – reading / rewriting XML files in folders and ZIPs
tabs/database_tab.py     – tab "GUID Database"
tabs/replace_tab.py      – tab "Replace Dummy GUIDs"
tabs/settings_tab.py     – tab "Settings"
"""

import os
import sys

# Make "core" and "tabs" importable regardless of the directory the script
# is started from (e.g. double-click, IDE run configuration).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import GUIDManagerApp  # noqa: E402  (import after sys.path tweak)


def main():
    """Create the main window and run the Tk event loop."""
    app = GUIDManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
