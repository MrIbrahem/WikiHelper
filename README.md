# Wiki Ref Workspace Manager

A lightweight internal web application for managing WikiText content by extracting `<ref>` tags, allowing user editing of reference-free text, and automatically restoring references.

## Features

- **Reference Extraction**: Automatically extracts `<ref>` tags (including open and self-closing refs) using `wikitextparser`
- **Placeholder System**: References are replaced with placeholders like `[ref1]`, `[ref2]`, etc.
- **Safe Storage**: Each workspace maintains immutable original content and reference data
- **Automatic Restoration**: References are restored automatically when saving edits
- **Dashboard**: View and manage all workspaces with sorting by last updated

## Project Structure

```
project/
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # This file
│
└── src/                # Application source code
    ├── app.py          # Flask application
    ├── config.py       # Configuration
    │
    ├── templates/      # Jinja2 templates
    │   ├── base.html       # Base template
    │   ├── index.html      # Dashboard
    │   ├── new.html        # New workspace form
    │   ├── edit.html       # Edit workspace
    │   ├── browse.html     # Browse workspace files
    │   └── view_file.html  # View specific file
    │
    ├── static/
    │   └── style.css   # Styles
    │
    └── wikiops/        # Wiki operations module
        ├── __init__.py
        ├── refs.py     # Reference extraction & restoration
        ├── storage.py  # Filesystem operations
        └── models.py   # Data structures
```

## Workspace Files

Each workspace contains exactly four files (plus metadata):

| File | Description | Editable |
|------|-------------|----------|
| `original.wiki` | Original WikiText as submitted | ❌ Immutable |
| `refs.json` | Extracted reference tags | ❌ Immutable |
| `editable.wiki` | Text with refs replaced by placeholders | ✅ User-editable |
| `restored.wiki` | Auto-generated with refs restored | 🔄 Auto-generated |
| `meta.json` | Workspace metadata | 🔄 Auto-updated |

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd WikiHelper
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env and set your configuration
   ```

5. Run the application:
   ```bash
   cd src
   python app.py
   ```

6. Open your browser and navigate to `http://localhost:5000`

## Configuration

Environment variables (set in `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `WIKI_WORK_ROOT` | Root directory for workspaces | `$HOME/data` |
| `FLASK_SECRET_KEY` | Secret key for sessions/CSRF | `change-me-in-production` |
| `FLASK_DEBUG` | Enable debug mode (0 or 1) | `0` |
| `MAX_CONTENT_LENGTH` | Maximum upload size in bytes | `5242880` (5MB) |

## Usage

### Creating a Workspace

1. Click "New Workspace" from the navigation
2. Enter a title (will be converted to a safe slug)
3. Paste your WikiText content
4. Submit to create the workspace

### Editing Content

1. From the dashboard, click "Edit" on a workspace
2. Modify the text in the editor (keeping `[refN]` placeholders where needed)
3. Click "Save & Restore References"
4. View the restored content with original `<ref>` tags

### Browsing Files

1. From the dashboard, click "Browse" on a workspace
2. View, download, or copy content from any file

## Security Notes

- **Path Traversal Protection**: Workspace slugs are strictly validated
- **Immutable Files**: `original.wiki` and `refs.json` cannot be modified after creation
- **CSRF Protection**: All forms are protected with CSRF tokens
- **Input Size Limits**: Maximum content length is enforced

## Design Decisions

- **Slug Generation**: Titles are converted to safe slugs using strict ASCII normalization
- **UTF-8 Encoding**: All files are read/written with UTF-8 encoding
- **Atomic Writes**: File writes use temporary files to ensure atomicity
- **Reference Ordering**: References are numbered by their position in the original text

## Reference Extraction & Restoration

WikiHelper's core functionality is built around extracting `<ref>` tags from WikiText and restoring them after editing. This allows users to edit content without worrying about complex reference markup.

### How Extraction Works

The extraction process uses the `wikitextparser` library to parse WikiText and identify all `<ref>` tags, including:
- **Standard refs**: `<ref>citation text</ref>`
- **Named refs**: `<ref name="source">citation text</ref>`
- **Self-closing refs**: `<ref name="source" />`

Each reference is replaced with a numbered placeholder like `[ref1]`, `[ref2]`, etc., and the original content is stored in a JSON map.

#### Extraction Example

**Input WikiText:**
```wikitext
Albert Einstein was a theoretical physicist<ref>Born March 14, 1879</ref> who developed
the theory of relativity<ref name="nobel">Nobel Prize in Physics, 1921</ref>. His work
is referenced frequently<ref name="nobel" />.
```

**Output (Editable Text):**
```wikitext
Albert Einstein was a theoretical physicist[ref1] who developed
the theory of relativity[ref2]. His work
is referenced frequently[ref3].
```

**Generated refs.json:**
```json
{
  "ref1": "<ref>Born March 14, 1879</ref>",
  "ref2": "<ref name=\"nobel\">Nobel Prize in Physics, 1921</ref>",
  "ref3": "<ref name=\"nobel\" />"
}
```

### How Restoration Works

When you save your edits, WikiHelper scans for `[refN]` placeholders and replaces each one with its original `<ref>` tag content from the stored JSON map. If a placeholder isn't found in the map, it's kept as-is (useful for adding new references manually).

#### Restoration Example

**Edited Text (with placeholders):**
```wikitext
Albert Einstein was a renowned theoretical physicist[ref1] best known for developing
the theory of relativity[ref2]. His groundbreaking work
is referenced frequently in modern physics[ref3].
```

**Output (Restored WikiText):**
```wikitext
Albert Einstein was a renowned theoretical physicist<ref>Born March 14, 1879</ref> best known for developing
the theory of relativity<ref name="nobel">Nobel Prize in Physics, 1921</ref>. His groundbreaking work
is referenced frequently in modern physics<ref name="nobel" />.
```

### Technical Implementation

The extraction and restoration functions can be used programmatically:

```python
from wikiops.refs import extract_refs_from_text, restore_refs_in_text

# Extraction
original_text = 'Hello<ref>World</ref> and <ref name="foo">Bar</ref>!'
editable_text, refs_map = extract_refs_from_text(original_text)
# editable_text: 'Hello[ref1] and [ref2]!'
# refs_map: {'ref1': '<ref>World</ref>', 'ref2': '<ref name="foo">Bar</ref>'}

# Restoration
modified_text = 'Hello[ref1] and [ref2]! Added more content.'
restored_text = restore_refs_in_text(modified_text, refs_map)
# restored_text: 'Hello<ref>World</ref> and <ref name="foo">Bar</ref>! Added more content.'
```

### Key Algorithm Details

1. **Stable Numbering**: References are numbered by their position in the original text, ensuring consistent placeholder assignment.
2. **Reverse Replacement**: During extraction, replacements are applied from end to start to preserve string indices.
3. **Exact Preservation**: The original `<ref>` content is stored as an exact substring slice, preserving all formatting, whitespace, and attributes.
4. **Graceful Handling**: Missing placeholders during restoration are kept as-is, allowing manual reference additions.

## License

MIT License
