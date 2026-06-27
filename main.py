# main.py
import os
from flask import Flask, render_template, redirect, url_for, jsonify, request
from dotenv import load_dotenv
from auth import auth_bp, get_logto_client

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.register_blueprint(auth_bp, url_prefix="/auth")


@app.route('/')
async def home():
    client = get_logto_client()
    if client.isAuthenticated():
        return redirect(url_for('dashboard'))
    return render_template('index.html', is_authenticated=False)


@app.route('/dashboard')
async def dashboard():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

    # Safely extract Logto user info to ensure Jinja can render it
    user_data = {"name": "Architect", "email": "No email provided"}
    try:
        user_info = await client.fetchUserInfo()

        # Extract dictionary from Logto UserInfoResponse Object
        if hasattr(user_info, 'model_dump'):
            info_dict = user_info.model_dump()
        elif hasattr(user_info, 'dict'):
            info_dict = user_info.dict()
        elif hasattr(user_info, '__dict__'):
            info_dict = vars(user_info)
        else:
            info_dict = user_info if isinstance(user_info, dict) else {}

        user_data["name"] = info_dict.get('name') or info_dict.get('username') or 'Architect'
        user_data["email"] = info_dict.get('email', 'No email provided')
    except Exception as e:
        print(f"Failed to fetch user info: {e}")

    return render_template('dashboard.html', user=user_data)


# ═══════════════════════════════════════════════════════════
# MOCK APIs / AGENT ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route('/api/setbacks/<city>', methods=['GET'])
def get_setbacks(city):
    db = {
        "seattle": {"front": 20, "rear": 25, "side": 5, "max_height": 30, "zone": "SF 5000"},
        "bellevue": {"front": 20, "rear": 20, "side": 15, "max_height": 35, "zone": "R-1"},
        "redmond": {"front": 15, "rear": 20, "side": 10, "max_height": 30, "zone": "R-4"},
        "bothell": {"front": 25, "rear": 25, "side": 8, "max_height": 35, "zone": "R 9600"}
    }
    return jsonify(db.get(city.lower(), db["seattle"]))


@app.route('/api/planning/chat', methods=['POST'])
def mock_planning_chat():
    data = request.json
    user_message = data.get('message', '').lower()

    if "bedroom" in user_message or "bed" in user_message:
        reply = "Got it. I'll prioritize spatial allocation for the bedrooms. Do you want a primary suite with an attached bath?"
    elif "kitchen" in user_message:
        reply = "Noted. I'll configure an open-plan kitchen towards the social zones. Any preference on island size?"
    else:
        reply = "Understood. I am adding this constraint to the brief. Review the updated parameters when you're ready."

    return jsonify({"reply": reply})


if __name__ == '__main__':
    app.run(debug=True)