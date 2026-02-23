# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WikiHelper is a Flask web application for managing WikiText content by extracting and restoring `<ref>` tags. It allows users to edit WikiText without dealing with complex reference markup, then automatically restores references when saving.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask application
cd src && python app.py
# Access at http://localhost:5000

# Run all tests
pytest

# Run specific test file
pytest tests/wikiops/test_refs_extract.py

# Run specific test
pytest tests/wikiops/test_refs_extract.py::test_extract_simple_ref -v
```

## Architecture

### Core Flow
1. **Extraction**: `wikiops.refs.extract_refs_from_text()` parses WikiText using `wikitextparser`, replaces `<ref>` tags with `[refN]` placeholders
2. **Restoration**: `wikiops.refs.restore_refs_in_text()` replaces placeholders back with original `<ref>` tags

### Module Structure (`src/wikiops/`)
- **refs.py**: Core extraction/restoration logic using wikitextparser
- **storage.py**: Workspace filesystem operations, path validation, atomic writes
- **wikipedia.py**: Fetch article content from Wikipedia API
- **utils.py**: Slugification, section header fixes
- **models.py**: Dataclasses for Workspace and metadata

### Workspace File Structure
Each workspace contains immutable and mutable files:
- `original.wiki` - **Immutable** original WikiText
- `refs.json` - **Immutable** extracted references map
- `editable.wiki` - User-editable content with placeholders
- `restored.wiki` - Auto-generated with refs restored
- `meta.json` - Workspace metadata

**Critical**: Never modify `original.wiki` or `refs.json` after creation.

### Flask Routes (`src/app.py`)
- `/` - Dashboard listing workspaces
- `/new` - Create workspace from pasted/uploaded WikiText
- `/import-wikipedia` - Import article from Wikipedia API
- `/w/<slug>/edit` - Edit editable.wiki
- `/w/<slug>/save` - Save and regenerate restored.wiki
- `/w/<slug>/browse` - Browse workspace files

## Key Implementation Details

- **UTF-8 encoding**: Mandatory for all file operations (supports multilingual content)
- **Reverse replacement**: During extraction, replacements apply end-to-start to preserve string indices
- **Path safety**: `safe_workspace_path()` validates slugs against traversal attacks and Windows reserved names
- **Atomic writes**: All file writes use temp files + atomic rename
- **User isolation**: Workspaces stored per-user via cookie-based username

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WIKI_WORK_ROOT` | Root directory for workspaces | `$HOME/data` |
| `FLASK_SECRET_KEY` | Secret key for sessions | *(required for production)* |
| `FLASK_DEBUG` | Enable debug mode (0/1) | `0` |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | `524288000` |
