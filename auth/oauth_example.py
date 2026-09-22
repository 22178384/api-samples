"""OAuth2 authorization-code flow, from scratch, with requests.

No oauthlib, no requests-oauthlib. Those are fine, but when the flow breaks you
end up debugging someone else's abstraction. This file is the whole thing in
~80 lines so you can see every step.

This is the flow for a *web server* app (you can keep a client secret). For a
SPA or mobile app, use PKCE without a secret. Don't ship this file as-is.

Endpoints are placeholders. Replace with your provider's:
  - GitHub:  https://github.com/login/oauth/authorize  / .../access_token
  - Google:  https://accounts.google.com/o/oauth2/v2/auth / .../token
"""

from __future__ import annotations

import os
import secrets
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

AUTHORIZE_URL = "https://auth.example.com/oauth/authorize"
TOKEN_URL = "https://auth.example.com/oauth/token"

CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:8000/callback")
SCOPES = ["read", "profile"]


def build_authorize_url(state: str | None = None) -> tuple[str, str]:
    """Return (url_to_redirect_user_to, state).

    The `state` param is CSRF protection. Generate it per login attempt, stash
    it in the user's session, and compare when the provider redirects back. If
    you skip this, an attacker can log a victim into the attacker's account.
    """
    state = state or secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}", state


def exchange_code_for_token(code: str) -> dict:
    """Trade the ?code=... from the callback for an access token.

    This is a back-channel POST (server-to-server), not a redirect. The code is
    single-use and short-lived (usually 10 minutes).
    """
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Accept": "application/json"},
        timeout=(3.05, 15.0),
    )
    # Providers return 400 with a JSON {"error": "invalid_grant"} for a bad code,
    # so read the body before raising.
    if resp.status_code != 200:
        raise RuntimeError(f"token exchange failed: {resp.status_code} {resp.text}")
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token.

    Access tokens are short (often 1h). Refresh tokens are long-lived and should
    be stored encrypted. Not every provider issues refresh tokens — Google only
    does when you pass access_type=offline.
    """
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=(3.05, 15.0),
    )
    resp.raise_for_status()
    return resp.json()


def call_api(access_token: str) -> dict:
    """Hit a protected resource with the bearer token."""
    resp = requests.get(
        "https://auth.example.com/api/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    # Step 1: send the user here.
    url, state = build_authorize_url()
    print("Open this in a browser:\n ", url)
    print(f"(remember state={state} for the callback)")

    # Step 2: your callback endpoint receives ?code=...&state=... .
    #         Verify state, then:
    code = input("Paste the ?code= value from the redirect: ").strip()
    if not code:
        print("no code, stopping")
        return

    tokens = exchange_code_for_token(code)
    print(f"got access_token (…{tokens['access_token'][-6:]}), "
          f"expires_in={tokens.get('expires_in')}s")

    # Step 3: use it. In real code, persist refresh_token and refresh when the
    # access token expires (or on the first 401).
    if "refresh_token" in tokens:
        print("refresh_token present; would store it encrypted")


if __name__ == "__main__":
    main()
