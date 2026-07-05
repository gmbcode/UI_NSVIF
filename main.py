# main.py
import os
from datetime import datetime, timezone

# 1. FIX EZDXF CACHE: Redirect ezdxf's cache to Vercel's writable /tmp directory
# MUST be set before importing ezdxf!
from dotenv import load_dotenv

load_dotenv()
os.environ["EZDXF_CACHE_DIR"] = "/tmp"

from flask import Flask, render_template, redirect, url_for, jsonify, request, send_file, session
import requests
import base64
import tempfile
import io

import ezdxf

from auth import auth_bp, get_logto_client

# 2. FIX MATPLOTLIB IMPORTS
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib import font_manager  # Required for the font fix

from ezdxf.addons.drawing import (
    RenderContext,
    Frontend
)
from ezdxf.addons.drawing.matplotlib import (
    MatplotlibBackend
)
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.register_blueprint(auth_bp, url_prefix="/auth")
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(supabase_url, supabase_key)

# 3. APPLY FONT FIX
# Make sure you have a .ttf file in your static folder!
font_path = os.path.join(os.path.dirname(__file__), 'static', 'OpenSans-Regular.ttf')

if os.path.exists(font_path):
    # Register the font with Matplotlib
    font_manager.fontManager.addfont(font_path)
    prop = font_manager.FontProperties(fname=font_path)

    # Force Matplotlib to use this font globally
    plt.rcParams['font.family'] = prop.get_name()
else:
    print(f"Warning: Font not found at {font_path}. DXF text might render incorrectly.")


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

    # --- ROLE CHECK START ---
    role = session.get('user_role')
    email = session.get('user_email')
    user_id = session.get('user_id')

    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role == 'Reviewer':
        return redirect(url_for('reviewer_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
    # --- ROLE CHECK END ---

    # Initialize default user data
    user_data = {
        "name": "Architect",
        "email": email or "No email provided"
    }

    # Fetch the actual name from Supabase using user_id
    if user_id:
        try:
            response = supabase.table("users").select("name").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                # Overwrite the default name with the Supabase name
                user_data["name"] = response.data[0].get("name") or "Architect"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    # The template will now render {{ user.name }} using the Supabase data
    return render_template('dashboard.html', user=user_data)


@app.route('/project-dashboard')
async def project_dashboard():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))
    role = session.get('user_role')
    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
    user_data = {"name": "Architect", "email": "No email provided"}
    try:
        user_info = await client.fetchUserInfo()
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

    return render_template('project_dashboard.html', user=user_data)


@app.route('/api/select-project', methods=['POST'])
def select_project():
    data = request.json or {}
    session['project_name'] = data.get('name', 'My Project')
    session['project_address'] = data.get('address', 'Unknown Address')
    return jsonify({"status": "success"})


@app.route('/studio')
async def studio():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))
    role = session.get('user_role')
    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
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

    return render_template('studio.html', user=user_data)


@app.route('/iteration')
async def iteration():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))
    role = session.get('user_role')
    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
    user_data = {"name": "Architect", "email": "No email provided"}
    try:
        user_info = await client.fetchUserInfo()
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

    return render_template('iteration.html', user=user_data)


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


@app.route('/multifloor')
async def multifloor():
    client = get_logto_client()

    if not client.isAuthenticated():
        return redirect(url_for('home'))
    role = session.get('user_role')
    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
    return render_template('multifloor.html')


@app.route('/api/multifloor-image', methods=['POST'])
def multifloor_image():
    response = requests.post(
        "http://16.176.176.187:8001/api/v1/generate-multifloor",
        json={"session_id": "sim_session_001"}
    )

    data = response.json()

    dxf_bytes = base64.b64decode(
        data["dxf"]["content_base64"]
    )

    with tempfile.NamedTemporaryFile(
            suffix=".dxf",
            delete=False
    ) as tmp:
        tmp.write(dxf_bytes)
        dxf_path = tmp.name

    doc = ezdxf.readfile(dxf_path)

    fig = Figure(figsize=(10, 10))
    ax = fig.add_axes([0, 0, 1, 1])

    context = RenderContext(doc)
    backend = MatplotlibBackend(ax)

    Frontend(context, backend).draw_layout(
        doc.modelspace()
    )

    png = io.BytesIO()

    fig.savefig(
        png,
        format="png",
        bbox_inches="tight"
    )

    png.seek(0)

    return send_file(
        png,
        mimetype="image/png"
    )


@app.route('/api/multifloor-dxf', methods=['POST'])
def multifloor_dxf():
    response = requests.post(
        "http://16.176.176.187:8001/api/v1/generate-multifloor",
        json={"session_id": "sim_session_001"}
    )

    data = response.json()

    dxf_bytes = base64.b64decode(
        data["dxf"]["content_base64"]
    )

    dxf_file = io.BytesIO(dxf_bytes)

    return send_file(
        dxf_file,
        mimetype="application/dxf",
        as_attachment=True,
        download_name="multifloor.dxf"
    )


@app.route('/outside-view')
async def outside_view():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))
    role = session.get('user_role')
    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Architect':
        return redirect(url_for('in_progress'))
    return render_template('outside_view.html')


@app.route('/complete-profile', methods=['GET', 'POST'])
async def complete_profile():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

    email = session.get('user_email')
    user_id = session.get('user_id')

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        role = request.form.get('role')

        if user_id:
            now_iso = datetime.now(timezone.utc).isoformat()

            # Insert/upsert new user profile into Supabase according to new schema
            try:
                supabase.table("users").upsert({
                    "user_id": user_id,
                    "email": email,
                    "name": full_name,
                    "last_login": now_iso
                    # Notice: "role" is omitted here to prevent a crash, as it is no longer
                    # in the database schema. The app will persist it via the session below.
                }).execute()
            except Exception as e:
                print(f"Failed to upsert user profile: {e}")

        # Maintain application logic by setting the role in the Flask session
        session['user_role'] = role

        if role == 'Architect':
            return redirect(url_for('dashboard'))
        elif role == 'User':
            return redirect(url_for('user_dashboard'))
        elif role == 'Reviewer':
            return redirect(url_for('reviewer_dashboard'))
        else:
            return redirect(url_for('in_progress'))

    return render_template('complete_profile.html', email=email)


@app.route('/in-progress')
async def in_progress():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

    # Optional: ensure specific roles aren't accidentally trapped here
    role = session.get('user_role')
    if role == 'Architect':
        return redirect(url_for('dashboard'))
    elif role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role == 'Reviewer':
        return redirect(url_for('reviewer_dashboard'))

    return render_template('in_progress.html')

@app.route('/user-dashboard')
async def user_dashboard():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

    # --- USER ROLE CHECK ---
    role = session.get('user_role')
    user_id = session.get('user_id')

    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'Architect':
        return redirect(url_for('dashboard'))
    elif role == 'Reviewer':
        return redirect(url_for('reviewer_dashboard'))
    elif role != 'User':
        return redirect(url_for('in_progress'))
    # -----------------------

    # Initialize default user data
    user_data = {
        "name": "Homeowner",
        "email": session.get('user_email') or "No email provided"
    }

    # Fetch the actual name from Supabase
    if user_id:
        try:
            response = supabase.table("users").select("name").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                user_data["name"] = response.data[0].get("name") or "Homeowner"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    return render_template('user_dashboard.html', user=user_data)

@app.route('/reviewer/dashboard')
async def reviewer_dashboard():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

    # --- REVIEWER ROLE CHECK ---
    role = session.get('user_role')
    user_id = session.get('user_id')

    if not role:
        return redirect(url_for('complete_profile'))
    if role == 'Architect':
        return redirect(url_for('dashboard'))
    elif role == 'User':
        return redirect(url_for('user_dashboard'))
    elif role != 'Reviewer':
        return redirect(url_for('in_progress'))
    # -----------------------

    # Initialize default user data
    user_data = {
        "name": "Reviewer",
        "email": session.get('user_email') or "No email provided"
    }

    # Fetch the actual name from Supabase
    if user_id:
        try:
            response = supabase.table("users").select("name").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                user_data["name"] = response.data[0].get("name") or "Reviewer"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    return render_template('reviewer_dashboard.html', user=user_data)
if __name__ == '__main__':
    app.run(debug=True)