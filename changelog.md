# Changelog

## 0.5.3

### Fixed
- Fixed folder prefix handling in relative file paths so that exactly one directory level above `/data/` is retained (e.g. `[ModName]/data/base/...`), regardless of whether the mod folder itself or a parent directory is selected.


## 0.5.2

### Added
- **Names as comment fallback** when registering a mod. If a GUID has no
  `GUID - comment` line, its name is used instead:
  1. `<Name>` from the asset's `<Standard>` block (Anno 117 and Anno 1800)
  2. `<Text>` of the entry in a `texts_*.xml` file. Both layouts are supported:
     text before `<LineId>` (Anno 117) and `<GUID>` before text (Anno 1800).
- **Settings -> General -> Language Comment**: defines which `texts_*.xml` file
  names are read from (e.g. `german` -> `texts_german.xml`). If the file does
  not exist or does not contain the GUID, `texts_english.xml` is used, then any
  other language file. Saved with Enter or when leaving the field.
- Import summary now also shows the number of imported names.

### Changed
- `GUID - comment` lines keep priority. A name is only stored if the GUID has
  no comment in the database yet, so existing comments are never overwritten.
- New default settings: Appearance Mode `Dark`, Color Theme `dark-blue`,
  Language `English`, Language Comment `english`. Existing `config.ini`
  values are kept.
- README updated: top bar, update check, names as fallback, Language Comment,
  building the EXE and GitHub Actions workflows.
