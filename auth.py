"""
Authentication Blueprint for PlotMySpace.

This module handles authentication using Logto and integrates with
Supabase for user data storage and session management. It provides
routes for sign-in, sign-out, and the authentication callback.
"""

import os
from datetime import datetime, timezone
from typing import Union, Any, Dict, Optional

from flask import Blueprint, session, redirect, url_for, request
from werkzeug.wrappers import Response
from logto import LogtoClient, LogtoConfig, Storage, UserInfoScope
from supabase import create_client, Client

# Initialize Supabase
supabase_url: str = os.environ.get("SUPABASE_URL", "")
supabase_key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(supabase_url, supabase_key)

auth_bp: Blueprint = Blueprint("auth", __name__)


class SessionStorage(Storage):
    """
    Storage adapter for Logto to use Flask's session object.
    
    This allows Logto to persist authentication tokens and state
    across requests for the current user.
    """

    def get(self, key: str) -> Union[str, None]:
        """
        Retrieve a value from the session.

        Args:
            key (str): The storage key.

        Returns:
            Union[str, None]: The stored value, or None if not found.
        """
        return session.get(key, None)

    def set(self, key: str, value: str) -> None:
        """
        Store a value in the session.

        Args:
            key (str): The storage key.
            value (str): The value to store.
        """
        session[key] = value

    def delete(self, key: str) -> None:
        """
        Remove a value from the session.

        Args:
            key (str): The storage key.
        """
        session.pop(key, None)


def get_logto_client() -> LogtoClient:
    """
    Initialize and return a LogtoClient instance.

    Returns:
        LogtoClient: The configured client for Logto authentication.
    """
    return LogtoClient(
        LogtoConfig(
            endpoint=os.environ.get("LOGTO_ENDPOINT", ""),
            appId=os.environ.get("LOGTO_APP_ID", ""),
            appSecret=os.environ.get("LOGTO_APP_SECRET", ""),
            scopes=[UserInfoScope.email],
        ),
        storage=SessionStorage(),
    )


@auth_bp.route("/sign-in")
async def sign_in() -> Response:
    """
    Handle the sign-in request by redirecting to Logto.

    Returns:
        Response: A Flask redirect response to the Logto sign-in page.
    """
    client: LogtoClient = get_logto_client()
    redirect_uri: str = url_for("auth.callback", _external=True)
    sign_in_url: str = await client.signIn(redirectUri=redirect_uri)
    return redirect(sign_in_url)


@auth_bp.route("/callback")
async def callback() -> Union[Response, tuple[str, int]]:
    """
    Handle the authentication callback from Logto.

    This function processes the callback, fetches user information,
    updates the Supabase database with login timestamp, and redirects
    the user to the appropriate dashboard or profile completion page.

    Returns:
        Union[Response, tuple[str, int]]: A Flask redirect response based
        on the user's role, or an error tuple if auth fails.
    """
    client: LogtoClient = get_logto_client()
    await client.handleSignInCallback(request.url)

    # Fetch user info to extract email and user_id (sub)
    try:
        user_info: Any = await client.fetchUserInfo()

        # Safely extract dictionary using your existing logic
        if hasattr(user_info, "model_dump"):
            info_dict: Dict[str, Any] = user_info.model_dump()
        elif hasattr(user_info, "dict"):
            info_dict: Dict[str, Any] = user_info.dict()
        elif hasattr(user_info, "__dict__"):
            info_dict: Dict[str, Any] = vars(user_info)
        else:
            info_dict: Dict[str, Any] = user_info if isinstance(user_info, dict) else {}

        email: Optional[str] = info_dict.get("email")
        user_id: Optional[str] = info_dict.get("sub")  # Maps to the new user_id column

        if not user_id:
            return "Error: No user ID provided by identity provider.", 400

        session["user_email"] = email
        session["user_id"] = user_id

        # Check Supabase for existing user using the new primary key (user_id)
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        now_iso: str = datetime.now(timezone.utc).isoformat()

        if response.data and len(response.data) > 0:
            user_record: Dict[str, Any] = response.data[0]

            # Update last_login based on new schema
            try:
                supabase.table("users").update({"last_login": now_iso}).eq(
                    "user_id", user_id
                ).execute()
            except Exception as e:
                print(f"Error updating last_login: {e}")

            # Note: The 'role' column is not in the new schema.
            # We attempt to fetch it in case it's added back, otherwise we fallback to complete_profile.
            role: Optional[str] = user_record.get("role")

            if role:
                session["user_role"] = role
                if role == "Architect":
                    return redirect(url_for("dashboard"))
                elif role == "User":
                    return redirect(url_for("user_dashboard"))
                else:
                    return redirect(url_for("in_progress"))
            else:
                return redirect(url_for("complete_profile"))
        else:
            # New user: direct them to complete profile
            return redirect(url_for("complete_profile"))

    except Exception as e:
        print(f"Auth callback error: {e}")
        return redirect(url_for("home"))


@auth_bp.route("/sign-out")
async def sign_out() -> Response:
    """
    Handle the sign-out request.

    Clears the local session and redirects to the Logto sign-out URL.

    Returns:
        Response: A Flask redirect response to the Logto sign-out page.
    """
    client: LogtoClient = get_logto_client()
    # Clear custom session data
    session.pop("user_email", None)
    session.pop("user_role", None)
    session.pop("user_id", None)

    redirect_uri: str = url_for("home", _external=True)
    sign_out_url: str = await client.signOut(postLogoutRedirectUri=redirect_uri)
    return redirect(sign_out_url)