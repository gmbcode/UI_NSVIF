# auth.py
import os
from flask import Blueprint, session, redirect, url_for, request
from logto import LogtoClient, LogtoConfig, Storage, UserInfoScope
from typing import Union

# Define the blueprint
auth_bp = Blueprint('auth', __name__)

# Logto needs a persistent storage mechanism to handle the OIDC state.
# We map it securely to Flask's built-in session storage.
class SessionStorage(Storage):
    def get(self, key: str) -> Union[str, None]:
        return session.get(key, None)

    def set(self, key: str, value: str) -> None:
        session[key] = value

    def delete(self, key: str) -> None:
        session.pop(key, None)

# Helper to generate the client dynamically using environment variables
def get_logto_client() -> LogtoClient:
    return LogtoClient(
        LogtoConfig(
            endpoint=os.environ.get('LOGTO_ENDPOINT', ''),
            appId=os.environ.get('LOGTO_APP_ID', ''),
            appSecret=os.environ.get('LOGTO_APP_SECRET', ''),
            # Explicitly request the email scope from Logto
            scopes=[UserInfoScope.email]
        ),
        storage=SessionStorage()
    )

@auth_bp.route("/sign-in")
async def sign_in():
    client = get_logto_client()
    # Logto requires an absolute URL to redirect back to after auth
    redirect_uri = url_for('auth.callback', _external=True)
    sign_in_url = await client.signIn(redirectUri=redirect_uri)
    return redirect(sign_in_url)

@auth_bp.route("/callback")
async def callback():
    client = get_logto_client()
    # Process the tokens returned by Logto
    await client.handleSignInCallback(request.url)
    return redirect(url_for('home'))

@auth_bp.route("/sign-out")
async def sign_out():
    client = get_logto_client()
    redirect_uri = url_for('home', _external=True)
    sign_out_url = await client.signOut(postLogoutRedirectUri=redirect_uri)
    return redirect(sign_out_url)