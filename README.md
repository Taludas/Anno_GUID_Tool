# Anno GUID Tool

### Support

---

*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>

---

**[English](#english) | [Deutsch](#deutsch)**

---

<a name="english"></a>

## English

A desktop tool for **Anno 117** and **Anno 1800** modders. It keeps track of
the GUIDs your mods use and replaces temporary dummy GUIDs with real, unused
GUIDs from your own GUID ranges.

### Features

- **Two games, two databases.** Anno 117 and Anno 1800 each have their own
  GUID database and their own GUID ranges. Choose the game in the selector
  above the tabs.
- **GUID database.**
  - Register mods from a folder or a ZIP archive.
  - Search by GUID, comment or file path.
  - Export to CSV.
  - Delete entries.
  - Move entries to the other game.
- **Comments.** Comments in the format `GUID - text` inside XML comments are
  read when a mod is registered and shown in their own column.
- **Dummy GUID replacement.** Dummy GUIDs in a mod are replaced with free
  GUIDs from your own ranges. Definitions and all references are updated.
- **Multiple GUID ranges per game.** You can define any number of own ranges
  and dummy ranges for each game.
- **Collision protection.** GUIDs that are already registered are never
  assigned again.
- **German and English UI.** Light, dark and system themes are available.

### Requirements

- Python 3 with Tkinter (included in the standard Windows installer)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

```bash
pip install customtkinter
```

### Getting started

```bash
python main.py
```

On first start:

1. Open **Settings → Anno 117 / Anno 1800** and enter your own GUID ranges
   and dummy GUID ranges.
2. Select the game in the game selector at the top.
3. Register your existing mods in the **GUID Database** tab so their GUIDs
   are known and never assigned again.

### Usage

#### Tab "GUID Database"

| Action | How |
|---|---|
| Register a mod | **Register Folder in DB** or **Register ZIP in DB** |
| Search | Type in the search field. It filters by GUID, comment and location. |
| Export | **Export .csv** writes `GUID;Comment;Location`, separated by `;` (UTF-8) |
| Delete | Button, `Del` key or right-click menu |
| Select all | `Ctrl+A` |
| Move to other game | Right-click → **Move to Anno 117 / Anno 1800** |
| Scroll horizontally | Scroll bar or `Shift` + mouse wheel |

When a mod is registered:

- Only GUIDs defined in `<GUID>` or `<LineId>` tags are registered.
- They must lie inside one of the **own GUID ranges** of the active game.
- Language files (`texts_english.xml`, `texts_german.xml`, …) are grouped as
  `texts_*.xml`.

**Comments.** The comment column is filled from XML comments that contain one
`GUID - text` entry per line:

```xml
<!--
2144009900 - Praefectus Specialists Name
2144009901 - Praefectus Specialists Description
-->
<!-- 2144009902 - Praefectus Adriana Name -->
```

- A comment may be in any XML file of the same mod.
- Normal hyphens, dashes (`–`, `—`) and non-breaking spaces are accepted as
  separators.
- A comment found during registration overwrites the stored one. GUIDs
  without a comment in the mod keep their stored comment.
- After the import, a summary shows how many comments were found, changed,
  unchanged or skipped, and how many names were imported.

**Names as fallback.** If a GUID has no `GUID - text` comment, its name is
used instead:

1. `<Name>` from the asset's `<Standard>` block (Anno 117 and Anno 1800)
2. `<Text>` of the entry in a `texts_*.xml` file. Both layouts are supported:
   text before `<LineId>` (Anno 117) and `<GUID>` before text (Anno 1800).
   `texts_english.xml` is preferred if several languages exist.

A name is only stored if the GUID has no comment in the database yet, so it
never overwrites an existing comment.

**Moving entries.** Comments and file locations are moved together with the
GUID. If the GUID already exists in the target database, the location lists
are merged.

#### Tab "Replace Dummy GUIDs"

1. Open the mod with **Open Folder** or **Open ZIP**. All dummy GUIDs, i.e.
   GUIDs inside a dummy range, are listed together with their files.
2. Choose where assignment starts:
   - **Automatic:** start at the first own GUID and fill all free gaps.
   - **Start GUID:** start at a value you enter.
3. Click **Assign & Replace Real GUIDs** and confirm the warning.

What happens:

- Dummies are assigned in ascending order to the next free GUID.
- If one own range is full, assignment continues in the next range.
- Every standalone occurrence of a dummy is replaced in all XML files. This
  includes `<GUID>`, references such as `<Product>`, ModOp attributes and
  `GUID - text` comments.
- Nothing is changed if there are not enough free GUIDs, or if you cancel.
- Afterwards, the tool offers to register the mod in the database.

> ⚠️ Files are overwritten directly and this **cannot be undone**. Keep a
> backup or use version control.

#### Tab "Settings"

| Sub tab | Content |
|---|---|
| **General** | Appearance mode, color theme (needs a restart), language |
| **Anno 117** | Own GUID ranges and dummy GUID ranges for Anno 117 |
| **Anno 1800** | Own GUID ranges and dummy GUID ranges for Anno 1800 |

How to edit ranges:

- **`+`** adds a row and **`✕`** removes it.
- **Save Ranges** saves both lists of that game. `Enter` in a field does the
  same.

Rules checked when you save:

- Start and end must be numbers, with start ≤ end.
- Each list needs at least one range.
- Ranges within one list must not overlap.
- Own ranges and dummy ranges of the same game must not overlap. Ranges of
  different games may overlap.

### Files

| File | Location | Content |
|---|---|---|
| `config.ini` | Working directory | General settings and GUID ranges per game |
| `guid_database_anno117.json` | Working directory | GUID database for Anno 117 |
| `guid_database_anno1800.json` | Working directory | GUID database for Anno 1800 |
| `version.txt` | Next to `main.py` (or the `.exe`) | Program version shown in the title, e.g. `v1.23.45` |

Example `config.ini`:

```ini
[SETTINGS]
appearance_mode = System
color_theme = blue
language = en
auto_assign = false
active_game = anno1800

[ANNO1800]
own_ranges = 1337471142-1337471999, 2144009900-2144009999
dummy_ranges = 1000000000-1000999999
```

Example database entry:

```json
"2144009900": {
    "comment": "Praefectus Specialists Name",
    "locations": ["data/config/gui/texts_*.xml"]
}
```

**Migration from older versions** happens automatically:

- An old `guid_database.json` becomes the Anno 1800 database. The original
  file is kept as `guid_database.json.bak`.
- Old single-range settings are converted to range lists.
- Old database entries are converted to the new format.

### Project structure

```
AnnoGUIDTool/
├── main.py                 Entry point
├── app.py                  Main window, game selector, translation, tab wiring
├── version.txt             Program version
├── core/
│   ├── constants.py        Program info, file names, default ranges, regex patterns
│   ├── translations.py     All UI texts (DE / EN)
│   ├── config_manager.py   config.ini, GUID range lists per game
│   ├── guid_database.py    JSON database, free GUID allocation, migration
│   ├── xml_scanner.py      Read and rewrite XML files in folders and ZIPs
│   └── version.py          Reads version.txt
└── tabs/
    ├── database_tab.py     Tab "GUID Database"
    ├── replace_tab.py      Tab "Replace Dummy GUIDs"
    └── settings_tab.py     Tab "Settings"
```

The modules in `core/` have no UI code. All code is documented in English.

**Customization:**

- Column widths of the GUID table: constants at the top of
  `tabs/database_tab.py`
- Program name and author: `core/constants.py`

### Author

**gz2k2**

---

<a name="deutsch"></a>

## Deutsch

Ein Desktop-Tool für Modder von **Anno 117** und **Anno 1800**. Es verwaltet
die GUIDs, die deine Mods verwenden, und ersetzt temporäre Dummy-GUIDs durch
echte, freie GUIDs aus deinen eigenen GUID Ranges.

### Funktionen

- **Zwei Spiele, zwei Datenbanken.** Anno 117 und Anno 1800 haben jeweils
  eine eigene GUID-Datenbank und eigene GUID Ranges. Das Spiel wählst du über
  die Auswahl oberhalb der Tabs.
- **GUID-Datenbank.**
  - Mods aus einem Ordner oder einem ZIP-Archiv registrieren.
  - Nach GUID, Kommentar oder Dateipfad suchen.
  - Als CSV exportieren.
  - Einträge löschen.
  - Einträge in das andere Spiel verschieben.
- **Kommentare.** Kommentare im Format `GUID - Text` in XML-Kommentaren werden
  beim Registrieren gelesen und in einer eigenen Spalte angezeigt.
- **Dummy-GUIDs ersetzen.** Dummy-GUIDs einer Mod werden durch freie GUIDs aus
  den eigenen Ranges ersetzt. Definitionen und alle Verweise werden angepasst.
- **Mehrere GUID Ranges pro Spiel.** Für jedes Spiel kannst du beliebig viele
  eigene Ranges und Dummy Ranges festlegen.
- **Schutz vor Doppelvergabe.** Bereits registrierte GUIDs werden nie erneut
  vergeben.
- **Oberfläche auf Deutsch und Englisch.** Helles, dunkles und System-Design
  stehen zur Wahl.

### Voraussetzungen

- Python 3 mit Tkinter (im Standard-Installer für Windows enthalten)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

```bash
pip install customtkinter
```

### Start

```bash
python main.py
```

Beim ersten Start:

1. Unter **Einstellungen → Anno 117 / Anno 1800** die eigenen GUID Ranges und
   die Dummy GUID Ranges eintragen.
2. Oben das Spiel auswählen.
3. Im Tab **GUID Datenbank** die vorhandenen Mods registrieren. So sind ihre
   GUIDs bekannt und werden nie erneut vergeben.

### Bedienung

#### Tab „GUID Datenbank“

| Aktion | So geht's |
|---|---|
| Mod registrieren | **Ordner in DB registrieren** oder **ZIP in DB registrieren** |
| Suchen | In das Suchfeld tippen. Es filtert nach GUID, Kommentar und Ort. |
| Exportieren | **Export .csv** schreibt `GUID;Kommentar;Ort`, getrennt durch `;` (UTF-8) |
| Löschen | Button, `Entf`-Taste oder Rechtsklick-Menü |
| Alle auswählen | `Strg+A` |
| In anderes Spiel verschieben | Rechtsklick → **Verschieben nach Anno 117 / Anno 1800** |
| Waagerecht scrollen | Scrollbalken oder `Shift` + Mausrad |

Beim Registrieren einer Mod:

- Registriert werden nur GUIDs, die in `<GUID>`- oder `<LineId>`-Tags
  definiert sind.
- Sie müssen in einer der **eigenen GUID Ranges** des aktiven Spiels liegen.
- Sprachdateien (`texts_english.xml`, `texts_german.xml`, …) werden zu
  `texts_*.xml` zusammengefasst.

**Kommentare.** Die Kommentarspalte wird aus XML-Kommentaren gefüllt, die pro
Zeile einen Eintrag `GUID - Text` enthalten:

```xml
<!--
2144009900 - Praefectus Specialists Name
2144009901 - Praefectus Specialists Description
-->
<!-- 2144009902 - Praefectus Adriana Name -->
```

- Ein Kommentar kann in einer beliebigen XML-Datei derselben Mod stehen.
- Als Trennzeichen gelten normale Bindestriche, Gedankenstriche (`–`, `—`)
  und geschützte Leerzeichen.
- Ein beim Registrieren gefundener Kommentar überschreibt den gespeicherten.
  GUIDs ohne Kommentar in der Mod behalten ihren gespeicherten Kommentar.
- Nach dem Import zeigt eine Übersicht, wie viele Kommentare gefunden,
  geändert, unverändert oder übersprungen und wie viele Namen übernommen
  wurden.

**Namen als Ersatz.** Hat eine GUID keinen `GUID - Text`-Kommentar, wird
stattdessen ihr Name verwendet:

1. `<Name>` aus dem `<Standard>`-Block des Assets (Anno 117 und Anno 1800)
2. `<Text>` des Eintrags in einer `texts_*.xml`. Beide Aufbauten werden
   erkannt: Text vor `<LineId>` (Anno 117) und `<GUID>` vor Text (Anno 1800).
   Bei mehreren Sprachen hat `texts_english.xml` Vorrang.

Ein Name wird nur gespeichert, wenn die GUID in der Datenbank noch keinen
Kommentar hat. Er überschreibt also nie einen vorhandenen Kommentar.

**Verschieben.** Kommentar und Dateipfade wandern zusammen mit der GUID mit.
Gibt es die GUID im Ziel schon, werden die Dateipfade zusammengeführt.

#### Tab „Dummy-GUIDs Ersetzen“

1. Die Mod mit **Ordner öffnen** oder **ZIP öffnen** laden. Alle Dummy-GUIDs,
   also GUIDs innerhalb einer Dummy Range, werden mit ihren Dateien angezeigt.
2. Festlegen, wo die Vergabe beginnt:
   - **Automatisch:** ab der ersten eigenen GUID, freie Lücken werden gefüllt.
   - **Start-GUID:** ab einem selbst eingegebenen Wert.
3. **Echte GUIDs zuweisen & Ersetzen** klicken und die Warnung bestätigen.

Was dabei passiert:

- Die Dummies erhalten in aufsteigender Reihenfolge die jeweils nächste freie
  GUID.
- Ist eine eigene Range voll, geht es in der nächsten Range weiter.
- Jedes alleinstehende Vorkommen eines Dummys wird in allen XML-Dateien
  ersetzt. Das umfasst `<GUID>`, Verweise wie `<Product>`, ModOp-Attribute und
  `GUID - Text`-Kommentare.
- Reichen die freien GUIDs nicht aus oder brichst du ab, wird nichts
  verändert.
- Danach bietet das Tool an, die Mod in der Datenbank zu registrieren.

> ⚠️ Die Dateien werden direkt überschrieben. Das lässt sich **nicht
> rückgängig machen**. Lege vorher ein Backup an oder nutze eine
> Versionsverwaltung.

#### Tab „Einstellungen“

| Untertab | Inhalt |
|---|---|
| **Allgemein** | Erscheinungsbild, Farbthema (Neustart nötig), Sprache |
| **Anno 117** | Eigene GUID Ranges und Dummy GUID Ranges für Anno 117 |
| **Anno 1800** | Eigene GUID Ranges und Dummy GUID Ranges für Anno 1800 |

So bearbeitest du Ranges:

- **`+`** fügt eine Zeile hinzu, **`✕`** entfernt sie.
- **Ranges speichern** speichert beide Listen des Spiels. `Enter` in einem
  Feld macht dasselbe.

Diese Regeln werden beim Speichern geprüft:

- Start und Ende müssen Zahlen sein, mit Start ≤ Ende.
- Jede Liste braucht mindestens eine Range.
- Ranges innerhalb einer Liste dürfen sich nicht überschneiden.
- Eigene Ranges und Dummy Ranges desselben Spiels dürfen sich nicht
  überschneiden. Ranges verschiedener Spiele dürfen sich überschneiden.

### Dateien

| Datei | Ort | Inhalt |
|---|---|---|
| `config.ini` | Arbeitsverzeichnis | Allgemeine Einstellungen und GUID Ranges pro Spiel |
| `guid_database_anno117.json` | Arbeitsverzeichnis | GUID-Datenbank für Anno 117 |
| `guid_database_anno1800.json` | Arbeitsverzeichnis | GUID-Datenbank für Anno 1800 |
| `version.txt` | Neben `main.py` (bzw. der `.exe`) | Programmversion für die Titelleiste, z. B. `v1.23.45` |

Die Formate von `config.ini` und den Datenbanken findest du oben im englischen
Teil unter [Files](#files).

**Übernahme aus älteren Versionen** erfolgt automatisch:

- Eine alte `guid_database.json` wird zur Anno 1800-Datenbank. Die
  Originaldatei bleibt als `guid_database.json.bak` erhalten.
- Alte Einzel-Ranges werden in Range-Listen umgewandelt.
- Alte Datenbankeinträge werden ins neue Format umgestellt.

### Projektstruktur

```
AnnoGUIDTool/
├── main.py                 Startpunkt
├── app.py                  Hauptfenster, Spielauswahl, Übersetzung, Verbindung der Tabs
├── version.txt             Programmversion
├── core/
│   ├── constants.py        Programminfo, Dateinamen, Standard-Ranges, Regex
│   ├── translations.py     Alle Texte (DE / EN)
│   ├── config_manager.py   config.ini, GUID Range-Listen pro Spiel
│   ├── guid_database.py    JSON-Datenbank, Vergabe freier GUIDs, Migration
│   ├── xml_scanner.py      XML-Dateien in Ordnern und ZIPs lesen und schreiben
│   └── version.py          Liest version.txt
└── tabs/
    ├── database_tab.py     Tab „GUID Datenbank“
    ├── replace_tab.py      Tab „Dummy-GUIDs Ersetzen“
    └── settings_tab.py     Tab „Einstellungen“
```

Die Module in `core/` enthalten keinen Oberflächen-Code. Der gesamte Code ist
auf Englisch dokumentiert.

**Anpassungen:**

- Spaltenbreiten der GUID-Tabelle: Konstanten oben in `tabs/database_tab.py`
- Programmname und Autor: `core/constants.py`

### Autor

**gz2k2**
