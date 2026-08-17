from authlib.integrations.starlette_client import OAuth

from app.core.config import Settings

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


def create_oauth_registry(settings: Settings) -> OAuth:
    oauth = OAuth()
    if settings.google_client_id is None or settings.google_client_secret is None:
        return oauth

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret.get_secret_value(),
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
        },
    )
    return oauth
