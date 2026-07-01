# main.py
import os

# 1. FIX EZDXF CACHE: Redirect ezdxf's cache to Vercel's writable /tmp directory
# MUST be set before importing ezdxf!
os.environ["EZDXF_CACHE_DIR"] = "/tmp"

from flask import Flask, render_template, redirect, url_for, jsonify, request, send_file
from dotenv import load_dotenv
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

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.register_blueprint(auth_bp, url_prefix="/auth")

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


@app.route('/studio')
async def studio():
    client = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for('home'))

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


if __name__ == '__main__':
    app.run(debug=True)
