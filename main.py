# main.py
import os
from flask import Flask, render_template
from dotenv import load_dotenv
from auth import auth_bp, get_logto_client

# Load variables from .env
load_dotenv()

app = Flask(__name__)
# Flask requires a secret key to securely sign the session cookie
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Register the authentication blueprint (routes will be prefixed with /auth)
app.register_blueprint(auth_bp, url_prefix="/auth")


@app.route('/')
async def home():
    client = get_logto_client()
    is_authenticated = client.isAuthenticated()

    user_info = None
    if is_authenticated:
        # fetchUserInfo fetches profile details (like email/name) from Logto
        try:
            user_info = await client.fetchUserInfo()
        except Exception as e:
            print(f"Failed to fetch user info: {e}")

    return render_template('index.html', is_authenticated=is_authenticated, user=user_info)


if __name__ == '__main__':
    app.run(debug=True)