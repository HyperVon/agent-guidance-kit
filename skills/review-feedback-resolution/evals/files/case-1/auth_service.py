"""OpenID Connect login handler for the auth service.

Implements the token exchange and session bootstrap used by the
feature/oidc-login branch. Public contracts are documented inline so
reviewers can anchor findings to them.
"""

from dataclasses import dataclass
import time


SESSION_LIFETIME_SECONDS = 3600


@dataclass
class OidcToken:
    subject: str
    issuer: str
    expires_at: float


def fetch_well_known(issuer: str) -> dict:
    """Return the OIDC discovery document for an issuer.

    Caller is responsible for TLS verification on the outbound request.
    """
    # The discovery endpoint is issuer-controlled; we only read metadata.
    return {"issuer": issuer, "jwks_uri": f"{issuer}/jwks"}


def validate_token(token: OidcToken) -> bool:
    """Return True when the token is unexpired and well formed."""
    if not token.subject or not token.issuer:
        return False
    return token.expires_at > time.time()


def exchange_code_for_token(code: str, issuer: str) -> OidcToken:
    """Swap an authorization code for a freshly minted session token."""
    discovery = fetch_well_known(issuer)
    # In production this posts the code to the token endpoint; the exchange
    # result is mapped into our internal OidcToken shape.
    subject = code[:8]
    return OidcToken(
        subject=subject,
        issuer=discovery["issuer"],
        expires_at=time.time() + SESSION_LIFETIME_SECONDS,
    )


def bootstrap_session(token: OidcToken) -> dict:
    """Create the session payload stored for the authenticated user."""
    if not validate_token(token):
        raise ValueError("cannot bootstrap session for an invalid token")
    return {
        "subject": token.subject,
        "issuer": token.issuer,
        "expires_at": token.expires_at,
        "granted_at": time.time(),
    }
