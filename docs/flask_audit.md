# Flask Application Audit Report

**Project**: WikiHelper
**Audit Date**: 2026-02-23
**Auditor**: Claude Code
**Reference Standards**: Flask Skill v2.0.0 (jezweb/claude-skills/flask)

---

## Executive Summary

This audit evaluates the WikiHelper Flask application against production-tested patterns from the Flask skill documentation. The codebase demonstrates solid security practices for filesystem operations and input validation, but deviates significantly from architectural best practices that are essential for maintainability, testing, and deployment.

**Overall Assessment**: The application works for its intended purpose but requires substantial refactoring to meet Flask production standards.

---

## Severity Legend

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **Critical** | Security vulnerability or breaking issue | Immediate fix required |
| **High** | Significant deviation from best practices | Should be fixed before production |
| **Medium** | Moderate issue affecting maintainability | Plan to fix in next sprint |
| **Low** | Minor improvement opportunity | Address when convenient |

---

## 1. Architectural Deficiencies

### 1.1 Missing Application Factory Pattern

**Severity**: High

**Current State** (`src/app.py:89`):
```python
app = Flask(__name__)
app.config.from_object(Config)

# Initialize CSRF protection for all forms.
csrf = CSRFProtect(app)
```

**Issue**: The application uses a global app instance created at import time. This prevents:
- Multiple app instances with different configurations (testing vs production)
- Clean circular import prevention
- Proper test isolation

**Required Pattern** (from Flask Skill):
```python
# app/__init__.py
def create_app(config_class=Config):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)

    # Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
```

**Action Items**:
1. Create `src/app/__init__.py` with `create_app()` factory function
2. Move extension initialization to `init_app()` pattern
3. Create `src/run.py` entry point
4. Update all imports to avoid circular dependencies

---

### 1.2 No Blueprint Organization

**Severity**: High

**Current State**: All 15 routes defined in single `app.py` file (724 lines)

**Routes by Category**:
- User management: `/set_user`, `/logout` (2 routes)
- Dashboard: `/` (1 route)
- Workspace creation: `/new`, `/import-wikipedia` (2 routes)
- Workspace operations: `/w/<slug>/edit`, `/w/<slug>/save`, `/w/<slug>/browse`, `/w/<slug>/file/<name>`, `/w/<slug>/download/<name>` (5 routes)

**Required Pattern** (from Flask Skill):
```
src/
├── app/
│   ├── __init__.py          # create_app factory
│   ├── extensions.py        # csrf, etc.
│   ├── main/                # Main blueprint
│   │   ├── __init__.py
│   │   └── routes.py        # index, set_user, logout
│   ├── workspaces/          # Workspace blueprint
│   │   ├── __init__.py
│   │   └── routes.py        # new, import, edit, save, browse, file, download
│   └── templates/
├── config.py
└── run.py
```

**Blueprint Definition Example**:
```python
# app/workspaces/__init__.py
from flask import Blueprint

bp = Blueprint("workspaces", __name__, url_prefix="/w")

from app.workspaces import routes  # Import AFTER bp creation
```

**Action Items**:
1. Create blueprint structure for main and workspaces modules
2. Move routes to appropriate blueprint files
3. Update all `url_for()` calls to use blueprint prefixes (e.g., `url_for('workspaces.edit', slug=slug)`)
4. Update templates to use blueprint-prefixed endpoint names

---

### 1.3 Extension Initialization in Main Module

**Severity**: Medium

**Current State** (`src/app.py:94`):
```python
csrf = CSRFProtect(app)
```

**Issue**: Extensions are instantiated with the app object at import time, preventing the factory pattern.

**Required Pattern**:
```python
# app/extensions.py
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()  # Create without app

# app/__init__.py
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)  # Bind to app in factory
    return app
```

---

## 2. Security Issues

### 2.1 Weak Session/Identity Management

**Severity**: High

**Current State** (`src/app.py:297`):
```python
resp.set_cookie("username", safe_username, max_age=30 * 24 * 60 * 60)
```

**Issues Identified**:
1. **No session signing**: Cookie contains raw username without Flask session protection
2. **No HttpOnly flag**: JavaScript can access the cookie (`document.cookie`)
3. **No Secure flag**: Cookie transmitted over HTTP connections
4. **No SameSite protection**: CSRF protection is weakened
5. **No server-side session storage**: Cannot invalidate sessions

**Required Pattern** (Flask session with SECRET_KEY):
```python
# config.py
class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")  # Required for production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # Set to False for local dev without HTTPS
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

# app.py
from flask import session

@app.route("/set_user", methods=["POST"])
def set_user():
    username = request.form.get("username", "").strip()
    # ... validation ...
    session.permanent = True
    session["username"] = safe_username
    return redirect(next_url)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("set_user"))
```

**Action Items**:
1. Replace cookie-based identity with Flask session
2. Add session security configuration to Config class
3. Update all `request.cookies.get("username")` to `session.get("username")`

---

### 2.2 Missing Security Headers

**Severity**: Medium

**Current State**: No security headers are set on responses

**Required Pattern**:
```python
# app/__init__.py
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    return response
```

---

### 2.3 Path Traversal Mitigation Incomplete

**Severity**: Low

**Current State** (`src/app.py:649`, `src/wikiops/storage.py:117`):
```python
workspace_path = safe_workspace_path(user_root, slug)
```

**Analysis**: The `safe_workspace_path()` function properly validates paths, but the validation logic is duplicated between `app.py` (`validate_username()`) and `storage.py` (`RESERVED_NAMES`).

**Recommendation**: Consolidate path validation into a single module:
```python
# app/security.py
from typing import Optional
import re

RESERVED_NAMES = {...}  # Single source of truth

def validate_path_component(name: str) -> Optional[str]:
    """Validate a path component for security."""
    if not name:
        return "Name cannot be empty"
    if ".." in name or "/" in name or "\\" in name:
        return "Name contains invalid characters"
    if name.lower() in RESERVED_NAMES:
        return "Name is reserved"
    return None
```

---

## 3. Configuration Issues

### 3.1 Config Class Instantiated at Import Time

**Severity**: Medium

**Current State** (`src/config.py:36-129`):
```python
class Config:
    _secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not _secret_key:
        warnings.warn(...)  # Warns at IMPORT time
    SECRET_KEY: Final[str] = _secret_key
```

**Issues**:
1. Warnings fire at import time, not at app creation
2. Cannot have multiple config instances with different values
3. `WIKI_WORK_ROOT` resolved at class definition time

**Required Pattern**:
```python
# config.py
import os
from pathlib import Path

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-key")
    WIKI_WORK_ROOT = Path(os.environ.get("WIKI_WORK_ROOT", "./data"))
    MAX_CONTENT_LENGTH = 524288000
    WTF_CSRF_ENABLED = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WIKI_WORK_ROOT = Path("./test_data")
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Force SECRET_KEY to be set
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY must be set in production")
```

---

### 3.2 Missing SECRET_KEY_FALLBACKS

**Severity**: Low

**Flask 3.1.0 Feature** (Issue #8 from skill docs): Support for key rotation via `SECRET_KEY_FALLBACKS`

**Required Pattern**:
```python
class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "new-key")
    SECRET_KEY_FALLBACKS = [
        os.environ.get("FLASK_SECRET_KEY_OLD_1"),
        os.environ.get("FLASK_SECRET_KEY_OLD_2"),
    ]
    SECRET_KEY_FALLBACKS = [k for k in SECRET_KEY_FALLBACKS if k]
```

---

## 4. Testing Infrastructure

### 4.1 No Flask Test Fixtures

**Severity**: High

**Current State** (`tests/conftest.py`): Only defines data fixtures, no app/client fixtures

**Required Pattern** (from Flask Skill):
```python
# tests/conftest.py
import pytest
from app import create_app
from config import TestingConfig

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()
```

**Missing Tests**: There are no integration tests for Flask routes - only unit tests for wikiops modules.

---

### 4.2 CSRF Not Disabled for Tests

**Severity**: Medium

**Current State**: No test configuration exists to disable CSRF

**Required Pattern**:
```python
# config.py
class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for form testing
```

---

## 5. Production Readiness

### 5.1 Using Development Server

**Severity**: Critical

**Current State** (`src/app.py:716-723`):
```python
if __name__ == "__main__":
    debug = app.config["DEBUG"] or "debug" in sys.argv
    app.run(debug=debug, host="0.0.0.0", port=5000)
```

**Issue**: `app.run()` uses Flask's development server which is NOT suitable for production. It cannot handle concurrent requests and has security vulnerabilities.

**Required Pattern**:
```python
# run.py (development only)
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

# Production: Use gunicorn
# gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

**Dockerfile**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]
```

---

### 5.2 No Request Rate Limiting

**Severity**: Medium

**Current State**: No rate limiting on any routes

**Required Pattern**:
```bash
pip install flask-limiter
```

```python
# app/extensions.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# app/__init__.py
limiter.init_app(app)

# app/workspaces/routes.py
@bp.route("/import-wikipedia", methods=["POST"])
@limiter.limit("5 per minute")  # Prevent Wikipedia API abuse
def import_wikipedia():
    ...
```

---

### 5.3 Missing Logging Configuration

**Severity**: Medium

**Current State**: No application logging configured

**Required Pattern**:
```python
# app/__init__.py
import logging
from logging.handlers import RotatingFileHandler
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    # ... setup ...

    if not app.debug and not app.testing:
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_handler = RotatingFileHandler(
            "logs/wikihelper.log", maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("WikiHelper startup")

    return app
```

---

## 6. Code Quality Issues

### 6.1 Missing Type Hints on Route Returns

**Severity**: Low

**Current State**: Inconsistent type hints on route functions

**Example** (`src/app.py:322-348`):
```python
@app.route("/")
def index() -> str:  # Actually returns Response via render_template
```

**Correct Pattern**:
```python
from flask import Response

@app.route("/")
def index() -> Response:
    """Dashboard - list all workspaces."""
    return render_template("index.html", ...)
```

---

### 6.2 Template Organization

**Severity**: Low

**Current State**: All templates in single `templates/` directory

**Required Pattern** (with blueprints):
```
app/
├── main/
│   ├── templates/
│   │   └── main/
│   │       ├── index.html
│   │       └── set_user.html
│   └── routes.py
├── workspaces/
│   ├── templates/
│   │   └── workspaces/
│   │       ├── new.html
│   │       ├── edit.html
│   │       └── browse.html
│   └── routes.py
└── templates/
    └── base.html  # Shared base template
```

---

## 7. Compliance Matrix

| Flask Skill Requirement | Status | Location |
|------------------------|--------|----------|
| Application factory pattern | ❌ Missing | N/A - app is global |
| Blueprint organization | ❌ Missing | N/A - all routes in app.py |
| Extensions in separate file | ❌ Missing | csrf in app.py |
| Import routes at bottom of `__init__.py` | ❌ N/A | No blueprints exist |
| Use `current_app` not `app` | ⚠️ Partial | Uses global `app` |
| Use `with app.app_context()` | ✅ Present | Not needed currently |
| Never import `app` in models | ✅ N/A | No models use app |
| Never store secrets in code | ✅ Present | Uses environment variables |
| Never use `app.run()` in production | ❌ Missing | app.py:723 |
| Never skip CSRF protection | ✅ Present | CSRFProtect enabled |
| Config classes for environments | ⚠️ Partial | Single Config class |
| Test fixtures for app/client | ❌ Missing | tests/conftest.py |

---

## 8. Action Plan

### Phase 1: Critical Security (Immediate)
1. Replace cookie-based identity with Flask session
2. Add security headers to all responses
3. Document that `app.run()` is for development only

### Phase 2: Architecture Refactoring (Before Production)
1. Implement application factory pattern
2. Create extensions.py module
3. Organize routes into blueprints
4. Add proper test fixtures

### Phase 3: Production Hardening (Before Deployment)
1. Add rate limiting
2. Configure production logging
3. Add Gunicorn to dependencies
4. Create Dockerfile
5. Add health check endpoint

### Phase 4: Nice-to-Have Improvements
1. Organize templates by blueprint
2. Add type hints consistently
3. Consolidate path validation
4. Add SECRET_KEY_FALLBACKS support

---

## 9. Code Examples

### Complete Factory Pattern Implementation

```python
# src/app/__init__.py
from flask import Flask
from config import Config
from app.extensions import csrf, limiter

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)
    limiter.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp
    from app.workspaces import bp as workspaces_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(workspaces_bp, url_prefix="/w")

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    return app
```

### Blueprint Route Migration Example

```python
# src/app/workspaces/routes.py (before in app.py)
@app.route("/w/<slug>/edit", methods=["GET"])
def edit_workspace(slug: str) -> str:
    # ... implementation ...
    return render_template("edit.html", ...)

# src/app/workspaces/routes.py (after migration)
from flask import Blueprint, render_template
from app.workspaces import bp

@bp.route("/<slug>/edit", methods=["GET"])
def edit_workspace(slug: str) -> Response:
    # ... same implementation ...
    return render_template("workspaces/edit.html", ...)
```

### Session-Based Identity Migration

```python
# Before (cookie-based)
resp = make_response(redirect(next_url))
resp.set_cookie("username", safe_username, max_age=30 * 24 * 60 * 60)

# After (session-based)
from flask import session
session.permanent = True
session["username"] = safe_username
return redirect(next_url)

# Before (retrieving)
username = request.cookies.get("username")

# After (retrieving)
username = session.get("username")
```

---

## 10. References

- [Flask Skill v2.0.0](.claude/flask/SKILL.md)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Application Factory Pattern](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [OWASP Flask Security Guide](https://flask.palletsprojects.com/en/stable/security/)

---

*Report generated by Claude Code. For questions or clarifications, refer to the Flask skill documentation.*
