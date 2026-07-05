# auth.py
import os
from datetime import datetime, timezone
from flask import Blueprint, session, redirect, url_for, request
from logto import LogtoClient, LogtoConfig, Storage, UserInfoScope
from typing import Union
from supabase import create_client, Client

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(supabase_url, supabase_key)

auth_bp = Blueprint('auth', __name__)


class SessionStorage(Storage):
    def get(self, key: str) -> Union[str, None]:
        return session.get(key, None)

    def set(self, key: str, value: str) -> None:
        session[key] = value

    def delete(self, key: str) -> None:
        session.pop(key, None)


def get_logto_client() -> LogtoClient:
    return LogtoClient(
        LogtoConfig(
            endpoint=os.environ.get('LOGTO_ENDPOINT', ''),
            appId=os.environ.get('LOGTO_APP_ID', ''),
            appSecret=os.environ.get('LOGTO_APP_SECRET', ''),
            scopes=[UserInfoScope.email]
        ),
        storage=SessionStorage()
    )


@auth_bp.route("/sign-in")
async def sign_in():
    client = get_logto_client()
    redirect_uri = url_for('auth.callback', _external=True)
    sign_in_url = await client.signIn(redirectUri=redirect_uri)
    return redirect(sign_in_url)


@auth_bp.route("/callback")
async def callback():
    client = get_logto_client()
    await client.handleSignInCallback(request.url)

    # Fetch user info to extract email and user_id (sub)
    try:
        user_info = await client.fetchUserInfo()

        # Safely extract dictionary using your existing logic
        if hasattr(user_info, 'model_dump'):
            info_dict = user_info.model_dump()
        elif hasattr(user_info, 'dict'):
            info_dict = user_info.dict()
        elif hasattr(user_info, '__dict__'):
            info_dict = vars(user_info)
        else:
            info_dict = user_info if isinstance(user_info, dict) else {}

        email = info_dict.get('email')
        user_id = info_dict.get('sub')  # Maps to the new user_id column

        if not user_id:
            return "Error: No user ID provided by identity provider.", 400

        session['user_email'] = email
        session['user_id'] = user_id

        # Check Supabase for existing user using the new primary key (user_id)
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        now_iso = datetime.now(timezone.utc).isoformat()

        if response.data and len(response.data) > 0:
            user_record = response.data[0]

            # Update last_login based on new schema
            try:
                supabase.table("users").update({"last_login": now_iso}).eq("user_id", user_id).execute()
            except Exception as e:
                print(f"Error updating last_login: {e}")

            # Note: The 'role' column is not in the new schema.
            # We attempt to fetch it in case it's added back, otherwise we fallback to complete_profile.
            role = user_record.get('role')

            if role:
                session['user_role'] = role
                if role == 'Architect':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('in_progress'))
            else:
                # If no role is found (due to the new schema), direct to complete_profile
                # so they can set it in the session for routing purposes.
                return redirect(url_for('complete_profile'))
        else:
            # New user: direct them to complete profile
            return redirect(url_for('complete_profile'))

    except Exception as e:
        print(f"Auth callback error: {e}")
        return redirect(url_for('home'))


@auth_bp.route("/sign-out")
async def sign_out():
    client = get_logto_client()
    # Clear custom session data
    session.pop('user_email', None)
    session.pop('user_role', None)
    session.pop('user_id', None)

    redirect_uri = url_for('home', _external=True)
    sign_out_url = await client.signOut(postLogoutRedirectUri=redirect_uri)
    return redirect(sign_out_url)