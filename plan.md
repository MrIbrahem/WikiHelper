# Wiki Ref Workspace Manager – Implementation Plan (Flask + Python)

## 1. Objective

Build a lightweight internal web application that manages long WikiText content by:
- Extracting `<ref>` tags (including open and self-closing refs) using **wikitextparser (wtp)**
- Allowing users to edit only the reference-free text
- Restoring references automatically
- Preserving the original text and references immutably after initial creation

The application must be implemented using **Python + Flask** with simple HTML (Jinja2).

---

## 2. Core Workflow

### Step A: Workspace Creation
User submits:
- **Title**
- **Long WikiText**

On submission:
1. Generate a **safe slug** from the title.
2. Create a folder named after the slug inside a root directory defined by an environment variable.
3. Inside the folder, create exactly **four files**:
   1. `original.wiki`  
      - Stores the original WikiText exactly as entered.
      - Written once only.
   2. `refs.json`  
      - JSON map of extracted `<ref>` tags.
      - Written once only.
   3. `editable.wiki`  
      - WikiText with `<ref>` tags replaced by placeholders `[ref1]`, `[ref2]`, etc.
      - User-editable.
   4. `restored.wiki`  
      - Result of restoring references after user edits.
      - Updated automatically by the system.

---

### Step B: Editing Phase
- User is redirected to an **edit page**.
- Page displays a `<textarea>` containing `editable.wiki`.
- User may translate, rewrite, or format the content freely.
- On submit:
  1. Update `editable.wiki`.
  2. Restore `<ref>` tags using `refs.json`.
  3. Save the restored output to `restored.wiki`.
  4. Display the restored result to the user.

> The user is **never allowed** to directly edit `original.wiki` or `refs.json`.

---

### Step C: Dashboard
A main page displays:
- List of all workspaces (folders)
- Sorted by last updated
- For each workspace:
  - Edit
  - Browse files
  - View metadata

---

## 3. Constraints and Rules

- Root workspace directory must be defined via environment variable:
  - `WIKI_WORK_ROOT`
- Folder names must be safe:
  - Strict slugification
  - No path traversal (`..`, `/`, `\`)
- If a workspace already exists:
  - Do **not** overwrite `original.wiki` or `refs.json`
- Only `editable.wiki` is user-editable
- All filesystem operations must be safe and atomic
- Maximum input size enforced via Flask config

---

## 4. Project Structure

```text
project/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── new.html
│   ├── edit.html
│   ├── browse.html
│   └── view_file.html
│
├── static/
│   └── style.css
│
└── wikiops/
    ├── __init__.py
    ├── refs.py        # wtp extraction & restoration
    ├── storage.py     # filesystem + slugify + safety
    └── models.py      # optional metadata structures
```
---

## 5. Workspace Folder Layout

Inside `WIKI_WORK_ROOT/<slug>/`:

original.wiki     # immutable original input refs.json         # immutable extracted references editable.wiki     # user-edited content (no refs) restored.wiki     # auto-generated restored output meta.json         # optional metadata (timestamps, counts)

---

## 6. Reference Handling Logic (wtp)

### Extraction
- Parse text with `wikitextparser.parse`
- Collect all `<ref>` tags:
  - `<ref>...</ref>`
  - `<ref name="x" />`
- Sort by position (`span`)
- Replace each with `[refN]`
- Store exact original substrings in `refs.json`

### Restoration
- Regex match: `\[ref\d+\]`
- Replace placeholders with original ref content from `refs.json`
- If placeholder missing, leave unchanged

---

## 7. Flask Routes

| Method | Route | Purpose |
|------|------|--------|
| GET | `/` | Dashboard |
| GET | `/new` | New workspace form |
| POST | `/new` | Create workspace |
| GET | `/w/<slug>/edit` | Edit `editable.wiki` |
| POST | `/w/<slug>/edit` | Update + restore |
| GET | `/w/<slug>/browse` | Browse workspace files |
| GET | `/w/<slug>/file/<name>` | View specific file |
| GET | `/w/<slug>/download/<name>` | Download file (optional) |

---

## 8. User Interface Requirements

- Minimal HTML, no JS frameworks
- Large textarea for editing
- Preview section for restored text
- Navigation:
  - Home
  - New Workspace
- Browse page to view all four files

---

## 9. Validation and Security

- Validate title length and content
- Enforce input size limits
- Slug generation must be deterministic and safe
- Ensure all file paths resolve within `WIKI_WORK_ROOT`
- Use `SECRET_KEY` from environment
- CSRF protection recommended

---

## 10. Environment Configuration

### `.env.example`

WIKI_WORK_ROOT=./data FLASK_SECRET_KEY=change-me FLASK_DEBUG=1

---

## 11. Dependencies

### `requirements.txt`

Flask python-dotenv wikitextparser Flask-WTF

---

## 12. Definition of Done

- Full workflow operational end-to-end
- Original content and references remain immutable
- Editable content updates correctly
- Restored output is accurate
- Dashboard lists and manages all workspaces
- Application runs locally with clear setup instructions

---

## 13. Implementation Policy

- Prefer safety over convenience
- Make deterministic decisions where unspecified
- Document assumptions in README
- Do not ask the user follow-up questions during implementation
