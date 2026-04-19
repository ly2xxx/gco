"""
GCO – Admin authentication helper.

Usage (on every page, after st.set_page_config):

    from auth import is_admin_user
    is_admin = is_admin_user()

Admin access: visit any page with ?admin=YOUR_SECRET_TOKEN in the URL.
The token must match one of the tokens in ADMIN_TOKENS (or ADMIN_TOKEN) in .streamlit/secrets.toml.
"""
import streamlit as st


def is_admin_user() -> bool:
    """Return True if the current request carries a valid admin token.

    Mechanism (same as local-media-player):
      • Admin visits the app with  ?admin=YOUR_SECRET_TOKEN
      • The token is compared against ADMIN_TOKEN or ADMIN_TOKENS stored in secrets.toml
      • Returns False for any visitor that does not supply the correct token
    """
    admin_param = st.query_params.get("admin", "")
    if not admin_param:
        return False

    try:
        # Check for multiple tokens first, then fall back to single token
        tokens = st.secrets.get("ADMIN_TOKENS", st.secrets.get("ADMIN_TOKEN", ""))
        
        # If it's a single string, wrap it in a list
        if isinstance(tokens, str):
            allowed_tokens = [tokens]
        else:
            allowed_tokens = list(tokens)

        return admin_param in allowed_tokens
    except Exception:
        return False
