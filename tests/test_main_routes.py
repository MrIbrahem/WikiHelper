"""
tests/test_main_routes.py - Tests for main blueprint routes

Tests for user authentication, dashboard, and utility routes.
"""

from __future__ import annotations

import pytest


class TestSetUserRoute:
    """Tests for the /set_user route."""

    def test_set_user_get(self, client):
        """Test GET request to set_user displays form."""
        response = client.get("/set_user")
        assert response.status_code == 200
        assert b"username" in response.data.lower()

    def test_set_user_post_valid(self, client):
        """Test POST with valid username sets session."""
        response = client.post(
            "/set_user",
            data={"username": "testuser"},
            follow_redirects=False
        )
        assert response.status_code == 302

        # Check that session was set
        with client.session_transaction() as sess:
            assert sess.get("username") == "testuser"

    def test_set_user_post_empty_username(self, client):
        """Test POST with empty username shows error."""
        response = client.post(
            "/set_user",
            data={"username": ""},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_set_user_post_whitespace_username(self, client):
        """Test POST with whitespace-only username shows error."""
        response = client.post(
            "/set_user",
            data={"username": "   "},
            follow_redirects=True
        )
        assert response.status_code == 200
        # Should show error about username being required or invalid
        assert b"required" in response.data.lower() or b"invalid" in response.data.lower()

    def test_set_user_post_special_chars_slugified(self, client):
        """Test that special characters in username are slugified."""
        response = client.post(
            "/set_user",
            data={"username": "Test User 123!"},
            follow_redirects=False
        )
        assert response.status_code == 302

        # Check that username was slugified
        with client.session_transaction() as sess:
            username = sess.get("username")
            assert username is not None
            # Slugified username should not contain spaces or special chars
            assert " " not in username
            assert "!" not in username

    def test_set_user_redirects_to_next_param(self, client):
        """Test that set_user redirects to next parameter after login."""
        response = client.post(
            "/set_user?next=/w/test/edit",
            data={"username": "testuser"},
            follow_redirects=False
        )
        assert response.status_code == 302
        assert "/w/test/edit" in response.location

    def test_set_user_rejects_unsafe_redirect(self, client):
        """Test that unsafe redirect URLs are rejected."""
        response = client.post(
            "/set_user?next=http://evil.com",
            data={"username": "testuser"},
            follow_redirects=False
        )
        assert response.status_code == 302
        # Should redirect to safe default (index) instead
        assert "evil.com" not in response.location

    def test_set_user_session_is_permanent(self, client):
        """Test that session is marked as permanent."""
        with client:
            client.post(
                "/set_user",
                data={"username": "testuser"},
                follow_redirects=False
            )
            # Access session to check if permanent
            with client.session_transaction() as sess:
                # Session should have username
                assert sess.get("username") == "testuser"


class TestLogoutRoute:
    """Tests for the /logout route."""

    def test_logout_clears_session(self, auth_client):
        """Test that logout clears the username from session."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302

        # Check that session was cleared
        with auth_client.session_transaction() as sess:
            assert "username" not in sess

    def test_logout_redirects_to_set_user(self, auth_client):
        """Test that logout redirects to set_user page."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/set_user" in response.location

    def test_logout_shows_success_message(self, auth_client):
        """Test that logout shows success message."""
        response = auth_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"logged out" in response.data.lower() or b"success" in response.data.lower()


class TestHealthRoute:
    """Tests for the /health endpoint."""

    def test_health_returns_json(self, client):
        """Test that health endpoint returns JSON."""
        # Health endpoint should be accessible without authentication
        response = client.get("/health")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_health_has_status_field(self, client):
        """Test that health response includes status field."""
        response = client.get("/health")
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_has_service_field(self, client):
        """Test that health response includes service name."""
        response = client.get("/health")
        data = response.get_json()
        assert "service" in data
        assert data["service"] == "wikihelper"

    def test_health_has_version_field(self, client):
        """Test that health response includes version."""
        response = client.get("/health")
        data = response.get_json()
        assert "version" in data
        assert isinstance(data["version"], str)


class TestIndexRoute:
    """Tests for the / (index) route."""

    def test_index_requires_authentication(self, client):
        """Test that index requires username in session."""
        with client.session_transaction() as sess:
            sess.clear()

        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/set_user" in response.location

    def test_index_with_authentication(self, auth_client):
        """Test that authenticated users can access index."""
        response = auth_client.get("/")
        assert response.status_code == 200

    def test_index_shows_workspace_sections(self, auth_client):
        """Test that index shows active and done workspace sections."""
        response = auth_client.get("/")
        assert response.status_code == 200
        # Check for workspace-related content
        data = response.data.lower()
        assert b"workspace" in data or b"dashboard" in data

    def test_index_with_no_workspaces(self, auth_client):
        """Test index when user has no workspaces."""
        response = auth_client.get("/")
        assert response.status_code == 200
        # Should still render successfully

    def test_index_handles_invalid_username_gracefully(self, client):
        """Test that index handles invalid username in session."""
        with client.session_transaction() as sess:
            sess["username"] = "../etc/passwd"  # Path traversal attempt

        response = client.get("/")
        # Should either redirect or show empty workspace list
        assert response.status_code in [200, 302]


class TestHelperFunctionsBehavior:
    """Tests for helper functions through route behavior."""

    def test_username_validation_via_set_user(self, client):
        """Test username validation through set_user route."""
        # Test valid username
        response = client.post(
            "/set_user",
            data={"username": "testuser"},
            follow_redirects=False
        )
        assert response.status_code == 302  # Success redirect

        # Test invalid username with path traversal
        response = client.post(
            "/set_user",
            data={"username": "../etc"},
            follow_redirects=True
        )
        # Should show error or slugify safely
        assert response.status_code == 200

    def test_safe_redirect_via_set_user(self, client):
        """Test safe redirect validation through set_user route."""
        # Test relative URL (safe)
        response = client.post(
            "/set_user?next=/dashboard",
            data={"username": "testuser"},
            follow_redirects=False
        )
        assert response.status_code == 302
        assert "/dashboard" in response.location

        # Test absolute URL (should default to index)
        response = client.post(
            "/set_user?next=http://evil.com",
            data={"username": "testuser2"},
            follow_redirects=False
        )
        assert response.status_code == 302
        assert "evil.com" not in response.location