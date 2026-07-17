"""
GCO – Admin authentication helper.

Usage (on every page, after st.set_page_config):

    from auth import is_admin_user
    is_admin = is_admin_user()

Admin access: visit any page with ?admin=YOUR_SECRET_TOKEN in the URL.
The token must match one of the tokens in ADMIN_TOKENS (or ADMIN_TOKEN) in .streamlit/secrets.toml.
Once validated, the token is remembered in st.session_state so admin mode
survives page navigation even if the query param is dropped.

Optional: map tokens to display names for the audit trail in secrets.toml:

    [ADMIN_NAMES]
    "token-of-alice" = "Alice"
    "token-of-bob"   = "Bob"
"""
import streamlit as st

_SESSION_KEY = "_gco_admin_token"


def _allowed_tokens() -> list[str]:
    """All valid admin tokens from secrets (ADMIN_TOKENS list or ADMIN_TOKEN string)."""
    try:
        tokens = st.secrets.get("ADMIN_TOKENS", st.secrets.get("ADMIN_TOKEN", ""))
    except Exception:
        return []
    if isinstance(tokens, str):
        return [tokens] if tokens else []
    return [t for t in tokens if t]


def is_admin_user() -> bool:
    """Return True if the current visitor carries (or previously supplied) a valid admin token.

    Mechanism:
      • Admin visits the app with  ?admin=YOUR_SECRET_TOKEN
      • The token is compared against ADMIN_TOKEN or ADMIN_TOKENS stored in secrets.toml
      • A valid token is cached in st.session_state so switching pages keeps admin mode
      • Returns False for any visitor without a valid token
    """
    allowed = _allowed_tokens()
    if not allowed:
        return False

    admin_param = st.query_params.get("admin", "")
    if admin_param in allowed:
        st.session_state[_SESSION_KEY] = admin_param
        return True

    return st.session_state.get(_SESSION_KEY) in allowed


def get_admin_name() -> str:
    """Display name of the current admin for the audit trail.

    Looks up the active token in the optional [ADMIN_NAMES] secrets table;
    falls back to "admin" when no mapping is configured.
    """
    token = st.session_state.get(_SESSION_KEY) or st.query_params.get("admin", "")
    if not token:
        return "admin"
    try:
        names = st.secrets.get("ADMIN_NAMES", {})
        name = names.get(token, "") if hasattr(names, "get") else ""
        return str(name) or "admin"
    except Exception:
        return "admin"
