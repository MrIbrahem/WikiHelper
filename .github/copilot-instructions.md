# WikiHelper - Copilot Instructions

## Project Overview

WikiHelper is a Python-based tool for managing WikiText content by extracting and restoring `<ref>` tags using the `wikitextparser` (wtp) library. The project is designed to help users work with long WikiText documents by temporarily removing reference tags, allowing cleaner editing, and then restoring them automatically.

## Technology Stack

- **Language**: Python 3.x
- **Web Framework**: Flask (planned)
- **Core Library**: wikitextparser (wtp) for WikiText parsing
- **Template Engine**: Jinja2 (for Flask templates)
- **Encoding**: UTF-8 (mandatory for multilingual content)

## Core Modules

### `extract_refs_wtp.py`
- Extracts `<ref>` tags from WikiText using wikitextparser
- Handles both opening/closing tags (`<ref>...</ref>`) and self-closing tags (`<ref name="x" />`)
- Replaces refs with placeholders like `[ref1]`, `[ref2]`, etc.
- Returns modified text and a refs map dictionary
- **Key function**: `extract_refs_from_text(text: str) -> Tuple[str, Dict[str, str]]`

### `restore_refs_wtp.py`
- Restores placeholders back to original `<ref>` tags
- Uses regex pattern `\[(ref\d+)\]` to find placeholders
- **Key function**: `restore_refs_in_text(text: str, refs_map: Dict[str, str]) -> str`

## Development Guidelines

### Code Style
- Use Python type hints for function signatures
- Follow PEP 8 conventions
- Import annotations from `__future__` for forward compatibility
- Use descriptive variable names

### File Handling
- **Always use UTF-8 encoding** when reading/writing files
- This is critical for handling multilingual WikiText content (Arabic, Chinese, etc.)
- Use `encoding='utf-8'` parameter explicitly in file operations

### WikiText Processing
- Sort tags by position (`span[0]`) to maintain stable numbering
- Apply replacements in reverse order to preserve string indices
- Store exact original substrings from `text[start:end]` to preserve formatting
- Handle missing placeholders gracefully (keep as-is if not found in refs_map)

### Security & Safety
- Implement strict path validation (prevent path traversal)
- Use slugification for folder/workspace names
- Validate input lengths and enforce content size limits
- No `.."`, `"/"`, or `"\"` in user-provided paths
- Set `MAX_CONTENT_LENGTH` for uploads/submissions

### Flask Application Structure (Planned)
```
project/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── templates/          # Jinja2 templates
├── static/             # CSS and static assets
└── wikiops/            # Core business logic
    ├── refs.py         # Extraction & restoration
    ├── storage.py      # Filesystem operations
    └── models.py       # Data models
```

### Workspace File Structure
Each workspace contains exactly four files:
1. `original.wiki` - Immutable original input (written once)
2. `refs.json` - Immutable extracted references map (written once)
3. `editable.wiki` - User-editable content (refs replaced with placeholders)
4. `restored.wiki` - Auto-generated output with refs restored

**Critical Rule**: Only `editable.wiki` is user-editable. Never modify `original.wiki` or `refs.json` after initial creation.

## Environment Configuration

Required environment variables:
- `WIKI_WORK_ROOT` - Root directory for workspace storage
- `FLASK_SECRET_KEY` - Secret key for Flask sessions
- `FLASK_DEBUG` - Debug mode flag (development only)

## Testing Considerations

- Test extraction with multiline `<ref>` tags
- Test self-closing tags like `<ref name="foo" />`
- Test restoration with missing placeholders
- Test slugification safety
- Verify UTF-8 encoding preservation

## Common Pitfalls to Avoid

1. **Don't** modify `original.wiki` or `refs.json` after workspace creation
2. **Don't** forget UTF-8 encoding in file operations
3. **Don't** allow path traversal in workspace names
4. **Don't** apply text replacements forward (use reverse order)
5. **Don't** assume ASCII-only content (support full Unicode)

## When Adding New Features

- Prioritize safety and data preservation
- Make deterministic decisions where behavior is unspecified
- Document assumptions in code comments or README
- Maintain immutability of original content and refs
- Follow the existing patterns in `extract_refs_wtp.py` and `restore_refs_wtp.py`

## Helpful Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app (when implemented)
flask run

# Test extraction (example)
python -c "from extract_refs_wtp import extract_refs_from_text; print(extract_refs_from_text('Hello <ref>world</ref>'))"
```

## Questions to Consider When Coding

1. Am I preserving UTF-8 encoding?
2. Am I validating/sanitizing user input?
3. Am I maintaining immutability of original content?
4. Am I handling edge cases (empty refs, malformed tags)?
5. Is my path handling safe from traversal attacks?

## Additional Resources

- Project plan: See `plan.md` for detailed implementation roadmap
- Arabic documentation: See `ar.md` for Arabic version of requirements
- wikitextparser docs: https://github.com/5j9/wikitextparser
