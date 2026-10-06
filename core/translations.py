"""
translations.py
===============

All user-facing UI texts of the application in German ("de") and English ("en").

How it works
------------
* Every UI element references a *translation key* (e.g. ``"btn_replace"``)
  instead of a hard-coded string.
* ``GUIDManagerApp.tr(key)`` looks the key up in the dictionary of the
  currently active language and returns the translated text.
* If a key is missing in the active language, the German dictionary is used
  as fallback; if it is missing there too, the key itself is returned.
* Some texts contain ``{}`` placeholders that are filled via ``str.format()``
  at runtime (e.g. counts, GUID ranges or file paths).

To add a new text: add the same key to BOTH language dictionaries.
"""

TRANSLATIONS = {
    "de": {
        "tab_db": "GUID Datenbank",
        "tab_assign": "Dummy-GUIDs Ersetzen",
        "tab_settings": "Einstellungen",
        "btn_import_folder": "Ordner in DB registrieren",
        "btn_import_zip": "ZIP in DB registrieren",
        "btn_export_csv": "Export .csv",
        "btn_delete": "Ausgewählte Einträge löschen",
        "search_ph": "DB nach GUID oder Datei filtern...",
        "guids_count": "Eingetragene GUIDs: {}",
        "tree_guid": "GUID",
        "tree_loc": "Ort",
        "btn_load_folder": "Ordner öffnen",
        "btn_load_zip": "ZIP öffnen",
        "no_path": "Kein Pfad geladen",
        "lbl_dummy_range": "Dummy GUID Range:",
        "lbl_start_guid": "Start-GUID (Range):",
        "chk_automatic": "Automatisch (freie GUIDs aus eigener Range)",
        "btn_replace": "Echte GUIDs zuweisen & Ersetzen",
        "found_dummies": "Gefundene eindeutige Dummy-GUIDs ({}):\n",
        "replace_done": "--- ERSETZUNG ABGESCHLOSSEN ---\n\n",
        "replaced_item": "Ersetzt: {}   --->   {}\n",
        "settings_appearance": "Erscheinungsbild (Mode):",
        "settings_theme": "Farbthema (Color Theme):",
        "settings_language": "Sprache (Language):",
        "msg_import_title": "Import abgeschlossen",
        "msg_import_body": "Analysierte XMLs: {}\nNeue Custom-GUIDs in DB registriert: {}",
        "msg_err_zip": "Fehler beim Lesen der ZIP-Datei",
        "msg_warn_load_mod": "Bitte zuerst eine Mod laden!",
        "msg_err_num": "Start-GUID muss eine Zahl sein!",
        "msg_no_dummies": "Keine Dummy-GUIDs innerhalb der Dummy GUID Range ({} – {}) gefunden.",
        "msg_ask_db_title": "In Datenbank eintragen?",
        "msg_ask_db_body": "{} GUIDs wurden zugewiesen.\nMöchtest du diese Mod direkt in die lokale Datenbank eintragen?",
        "msg_confirm_delete_title": "Einträge löschen",
        "msg_confirm_delete_body": "Möchtest du die {} ausgewählten Einträge wirklich aus der Datenbank löschen?",
        "msg_theme_restart_title": "Neustart erforderlich",
        "msg_theme_restart_body": "Das Farbthema wurde gespeichert.\nBitte starte die Anwendung neu, um das neue Theme vollständig zu übernehmen.",
        "msg_export_success_title": "Export erfolgreich",
        "msg_export_success_body": "Die Daten wurden erfolgreich in die CSV-Datei exportiert.",
        "msg_export_empty_title": "Export nicht möglich",
        "msg_export_empty_body": "Die Datenbank enthält keine Einträge zum Exportieren.",
        "settings_guid_range": "Eigene GUID Range:",
        "lbl_range_start": "Start:",
        "lbl_range_end": "Ende:",
        "btn_save_range": "Speichern",
        "lbl_range_info": "Eigene Range: {} – {}",
        "msg_range_saved_title": "GUID Range gespeichert",
        "msg_range_saved_body": "Eigene GUID Range gespeichert:\n{} – {}",
        "msg_err_range_num": "Start- und End-GUID müssen positive Zahlen sein!",
        "msg_err_range_order": "Die Start-GUID muss kleiner oder gleich der End-GUID sein!",
        "msg_err_start_outside": "Die Start-GUID liegt außerhalb der eigenen GUID Range ({} – {})!",
        "msg_err_range_exhausted": "Die eigene GUID Range ({} – {}) reicht nicht aus.\nBenötigt: {} GUIDs, verfügbar ab Start-GUID: {}.\nEs wurden keine Dateien verändert.",
        "settings_dummy_range": "Dummy GUID Range:",
        "msg_dummy_saved_title": "Dummy GUID Range gespeichert",
        "msg_dummy_saved_body": "Dummy GUID Range gespeichert:\n{} – {}",
        "msg_err_overlap": "Dummy GUID Range und eigene GUID Range dürfen sich nicht überschneiden!\nEigene Range: {} – {}\nDummy Range: {} – {}"
    },
    "en": {
        "tab_db": "GUID Database",
        "tab_assign": "Replace Dummy GUIDs",
        "tab_settings": "Settings",
        "btn_import_folder": "Register Folder in DB",
        "btn_import_zip": "Register ZIP in DB",
        "btn_export_csv": "Export .csv",
        "btn_delete": "Delete Selected Entries",
        "search_ph": "Filter DB by GUID or file...",
        "guids_count": "Registered GUIDs: {}",
        "tree_guid": "GUID",
        "tree_loc": "Location",
        "btn_load_folder": "Open Folder",
        "btn_load_zip": "Open ZIP",
        "no_path": "No path loaded",
        "lbl_dummy_range": "Dummy GUID Range:",
        "lbl_start_guid": "Start GUID (Range):",
        "chk_automatic": "Automatic (free GUIDs from own range)",
        "btn_replace": "Assign & Replace Real GUIDs",
        "found_dummies": "Found unique Dummy GUIDs ({}):\n",
        "replace_done": "--- REPLACEMENT COMPLETED ---\n\n",
        "replaced_item": "Replaced: {}   --->   {}\n",
        "settings_appearance": "Appearance Mode:",
        "settings_theme": "Color Theme:",
        "settings_language": "Language:",
        "msg_import_title": "Import Complete",
        "msg_import_body": "Analyzed XMLs: {}\nNew custom GUIDs registered in DB: {}",
        "msg_err_zip": "Error reading ZIP file",
        "msg_warn_load_mod": "Please load a mod first!",
        "msg_err_num": "Start GUID must be a number!",
        "msg_no_dummies": "No dummy GUIDs found within the dummy GUID range ({} – {}).",
        "msg_ask_db_title": "Add to Database?",
        "msg_ask_db_body": "{} GUIDs assigned.\nWould you like to register this mod directly into the local database?",
        "msg_confirm_delete_title": "Delete Entries",
        "msg_confirm_delete_body": "Are you sure you want to delete the {} selected entries from the database?",
        "msg_theme_restart_title": "Restart Required",
        "msg_theme_restart_body": "The color theme has been saved.\nPlease restart the application to fully apply the new color theme.",
        "msg_export_success_title": "Export Successful",
        "msg_export_success_body": "Data was successfully exported to the CSV file.",
        "msg_export_empty_title": "Export Not Possible",
        "msg_export_empty_body": "The database contains no entries to export.",
        "settings_guid_range": "Own GUID Range:",
        "lbl_range_start": "Start:",
        "lbl_range_end": "End:",
        "btn_save_range": "Save",
        "lbl_range_info": "Own range: {} – {}",
        "msg_range_saved_title": "GUID Range Saved",
        "msg_range_saved_body": "Own GUID range saved:\n{} – {}",
        "msg_err_range_num": "Start and end GUID must be positive numbers!",
        "msg_err_range_order": "Start GUID must be less than or equal to end GUID!",
        "msg_err_start_outside": "Start GUID is outside your own GUID range ({} – {})!",
        "msg_err_range_exhausted": "Your own GUID range ({} – {}) is not large enough.\nRequired: {} GUIDs, available from start GUID: {}.\nNo files were modified.",
        "settings_dummy_range": "Dummy GUID Range:",
        "msg_dummy_saved_title": "Dummy GUID Range Saved",
        "msg_dummy_saved_body": "Dummy GUID range saved:\n{} – {}",
        "msg_err_overlap": "Dummy GUID range and own GUID range must not overlap!\nOwn range: {} – {}\nDummy range: {} – {}"
    }
}
