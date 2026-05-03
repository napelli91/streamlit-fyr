import json
import uuid
from datetime import datetime, timezone

import streamlit as st
from extra_streamlit_components import CookieManager

from .backends.base import Backend

_COOKIE_KEY = "st_fyr_cookies"
_VISITOR_COOKIE = "visitor_id"
_COOKIE_EXPIRY = datetime(2030, 1, 1)


class Tracker:
    def __init__(self, app_name: str, backend: Backend):
        self.app_name = app_name
        self.backend = backend

    def init(self) -> None:
        """Initialize session tracking. Call once in app.py before pg.run().

        Resolves a persistent visitor_id from a browser cookie (two-render
        pattern due to CookieManager's async load), then generates a session_id
        and fires session_start exactly once per browser session.
        """
        self._resolve_visitor_id()
        if "visitor_id" in st.session_state and "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
            self._write("session_start")

    def page(self, page_name: str) -> None:
        """Track a page view and set the current page context.

        Call at the top of each page function so subsequent events
        on that page inherit the correct page name.

        Args:
            page_name: Human-readable page identifier (e.g. "dashboard").
        """
        st.session_state["_current_page"] = page_name
        self._write("page_view", {"page": page_name})

    def identify(self, user_id: str) -> None:
        """Associate subsequent events with a known user identity.

        Call after login resolves. The value is stored in session state and
        attached to every event for the remainder of the session.

        Args:
            user_id: An opaque identifier from your auth layer (e.g. an internal
                     user ID). Avoid raw email addresses — see README for guidance.
        """
        st.session_state["_user_id"] = user_id

    def event(self, name: str, properties: dict | None = None) -> None:
        """Track a custom interaction event.

        Args:
            name: Event name (e.g. "filter_applied", "audio_played").
            properties: Optional dict of additional context.
        """
        self._write(name, properties)

    def _resolve_visitor_id(self) -> None:
        """Resolve visitor_id from cookie into session_state.

        CookieManager is async — on the first render it returns None while
        its iframe loads, then triggers a Streamlit rerun. We use a
        _visitor_cookie_checked flag to distinguish "loading" (render 1) from
        "confirmed absent" (render 2), so we never overwrite a returning
        visitor's cookie before it has loaded.
        """
        if "visitor_id" in st.session_state:
            return

        cookie_manager = CookieManager(key=_COOKIE_KEY)
        visitor_id = cookie_manager.get(_VISITOR_COOKIE)

        if visitor_id is not None:
            st.session_state.visitor_id = visitor_id
        elif "_visitor_cookie_checked" in st.session_state:
            new_id = str(uuid.uuid4())
            cookie_manager.set(_VISITOR_COOKIE, new_id, expires_at=_COOKIE_EXPIRY)
            st.session_state.visitor_id = new_id
        else:
            st.session_state._visitor_cookie_checked = True

    def _write(self, event: str, properties: dict | None = None) -> None:
        self.backend.write(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": st.session_state.get("session_id", None),
                "visitor_id": st.session_state.get("visitor_id", None),
                "user_id": st.session_state.get("_user_id", None),
                "app_name": self.app_name,
                "page": st.session_state.get("_current_page"),
                "event": event,
                "properties": json.dumps(properties or {}),
            }
        )
