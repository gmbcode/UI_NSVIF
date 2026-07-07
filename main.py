"""
PlotMySpace Main Application.

This module initializes the Flask application, configures the environment,
handles routing for different personas, and integrates with external APIs
for CAD rendering and mock AI endpoints.
"""

import os
import base64
import tempfile
import io
from datetime import datetime, timezone
from typing import Union, Any, Dict, Optional

# 1. FIX EZDXF CACHE: Redirect ezdxf's cache to Vercel's writable /tmp directory
# MUST be set before importing ezdxf!
from dotenv import load_dotenv

load_dotenv()
os.environ["EZDXF_CACHE_DIR"] = "/tmp"

from flask import Flask, render_template, redirect, url_for, jsonify, request, send_file, session
from werkzeug.wrappers import Response
import requests

import ezdxf

from auth import auth_bp, get_logto_client

# 2. FIX MATPLOTLIB IMPORTS
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib import font_manager  # Required for the font fix

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from supabase import create_client, Client
from logto import LogtoClient

app: Flask = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.register_blueprint(auth_bp, url_prefix="/auth")
supabase_url: str = os.environ.get("SUPABASE_URL", "")
supabase_key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(supabase_url, supabase_key)

# 3. APPLY FONT FIX
# Make sure you have a .ttf file in your static folder!
font_path: str = os.path.join(os.path.dirname(__file__), "static", "OpenSans-Regular.ttf")

if os.path.exists(font_path):
    # Register the font with Matplotlib
    font_manager.fontManager.addfont(font_path)
    prop: font_manager.FontProperties = font_manager.FontProperties(fname=font_path)

    # Force Matplotlib to use this font globally
    plt.rcParams["font.family"] = prop.get_name()
else:
    print(f"Warning: Font not found at {font_path}. DXF text might render incorrectly.")


@app.route("/")
async def home() -> Union[Response, str]:
    """
    Render the home page or redirect to the dashboard if authenticated.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if client.isAuthenticated():
        return redirect(url_for("dashboard"))
    return render_template("index.html", is_authenticated=False)


@app.route("/dashboard")
async def dashboard() -> Union[Response, str]:
    """
    Render the Architect dashboard.

    Ensures the user is authenticated and has the 'Architect' role.
    Fetches the user's name from Supabase.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    # --- ROLE CHECK START ---
    role: Optional[str] = session.get("user_role")
    email: Optional[str] = session.get("user_email")
    user_id: Optional[str] = session.get("user_id")

    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role == "Reviewer":
        return redirect(url_for("reviewer_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
    # --- ROLE CHECK END ---

    # Initialize default user data
    user_data: Dict[str, str] = {
        "name": "Architect",
        "email": email or "No email provided",
    }

    # Fetch the actual name from Supabase using user_id
    if user_id:
        try:
            response = (
                supabase.table("users").select("name").eq("user_id", user_id).execute()
            )
            if response.data and len(response.data) > 0:
                # Overwrite the default name with the Supabase name
                user_data["name"] = response.data[0].get("name") or "Architect"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    # The template will now render {{ user.name }} using the Supabase data
    return render_template("dashboard.html", user=user_data)


@app.route("/feasibility")
async def feasibility() -> Union[Response, str]:
    """
    Render the Feasibility tool view.

    Requires the 'Architect' role. Fetches user details from Supabase.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    # --- ROLE CHECK START ---
    role: Optional[str] = session.get("user_role")
    email: Optional[str] = session.get("user_email")
    user_id: Optional[str] = session.get("user_id")

    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role == "Reviewer":
        return redirect(url_for("reviewer_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
    # --- ROLE CHECK END ---

    # Initialize default user data
    user_data: Dict[str, str] = {
        "name": "Architect",
        "email": email or "No email provided",
    }

    # Fetch the actual name from Supabase using user_id
    if user_id:
        try:
            response = (
                supabase.table("users").select("name").eq("user_id", user_id).execute()
            )
            if response.data and len(response.data) > 0:
                # Overwrite the default name with the Supabase name
                user_data["name"] = response.data[0].get("name") or "Architect"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    return render_template("feasibility.html", user=user_data)


@app.route("/project-dashboard")
async def project_dashboard() -> Union[Response, str]:
    """
    Render the detailed project dashboard.

    Requires the 'Architect' role. Uses Logto client user info.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))
    
    role: Optional[str] = session.get("user_role")
    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
        
    user_data: Dict[str, str] = {"name": "Architect", "email": "No email provided"}
    try:
        user_info: Any = await client.fetchUserInfo()
        if hasattr(user_info, "model_dump"):
            info_dict: Dict[str, Any] = user_info.model_dump()
        elif hasattr(user_info, "dict"):
            info_dict: Dict[str, Any] = user_info.dict()
        elif hasattr(user_info, "__dict__"):
            info_dict: Dict[str, Any] = vars(user_info)
        else:
            info_dict: Dict[str, Any] = user_info if isinstance(user_info, dict) else {}

        user_data["name"] = (
            info_dict.get("name") or info_dict.get("username") or "Architect"
        )
        user_data["email"] = info_dict.get("email", "No email provided")
    except Exception as e:
        print(f"Failed to fetch user info: {e}")

    return render_template("project_dashboard.html", user=user_data)


@app.route("/api/select-project", methods=["POST"])
def select_project() -> Response:
    """
    Select an active project and store it in the session.

    Returns:
        Response: A JSON response confirming success.
    """
    data: Dict[str, Any] = request.json or {}
    session["project_name"] = data.get("name", "My Project")
    session["project_address"] = data.get("address", "Unknown Address")
    return jsonify({"status": "success"})


@app.route("/studio")
async def studio() -> Union[Response, str]:
    """
    Render the Studio workspace.

    Requires the 'Architect' role. Retrieves Logto user information.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))
        
    role: Optional[str] = session.get("user_role")
    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
        
    user_data: Dict[str, str] = {"name": "Architect", "email": "No email provided"}
    try:
        user_info: Any = await client.fetchUserInfo()

        # Extract dictionary from Logto UserInfoResponse Object
        if hasattr(user_info, "model_dump"):
            info_dict: Dict[str, Any] = user_info.model_dump()
        elif hasattr(user_info, "dict"):
            info_dict: Dict[str, Any] = user_info.dict()
        elif hasattr(user_info, "__dict__"):
            info_dict: Dict[str, Any] = vars(user_info)
        else:
            info_dict: Dict[str, Any] = user_info if isinstance(user_info, dict) else {}

        user_data["name"] = (
            info_dict.get("name") or info_dict.get("username") or "Architect"
        )
        user_data["email"] = info_dict.get("email", "No email provided")
    except Exception as e:
        print(f"Failed to fetch user info: {e}")

    return render_template("studio.html", user=user_data)


@app.route("/iteration")
async def iteration() -> Union[Response, str]:
    """
    Render the Iteration view for reviewing variations.

    Requires the 'Architect' role. Retrieves Logto user information.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))
        
    role: Optional[str] = session.get("user_role")
    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
        
    user_data: Dict[str, str] = {"name": "Architect", "email": "No email provided"}
    try:
        user_info: Any = await client.fetchUserInfo()
        
        if hasattr(user_info, "model_dump"):
            info_dict: Dict[str, Any] = user_info.model_dump()
        elif hasattr(user_info, "dict"):
            info_dict: Dict[str, Any] = user_info.dict()
        elif hasattr(user_info, "__dict__"):
            info_dict: Dict[str, Any] = vars(user_info)
        else:
            info_dict: Dict[str, Any] = user_info if isinstance(user_info, dict) else {}

        user_data["name"] = (
            info_dict.get("name") or info_dict.get("username") or "Architect"
        )
        user_data["email"] = info_dict.get("email", "No email provided")
    except Exception as e:
        print(f"Failed to fetch user info: {e}")

    return render_template("iteration.html", user=user_data)


# ═══════════════════════════════════════════════════════════
# MOCK APIs / AGENT ENDPOINTS
# ═══════════════════════════════════════════════════════════


@app.route("/api/setbacks/<city>", methods=["GET"])
def get_setbacks(city: str) -> Response:
    """
    Retrieve setback configuration for a given city.

    Args:
        city (str): The name of the city.

    Returns:
        Response: A JSON response containing setback properties.
    """
    db: Dict[str, Dict[str, Any]] = {
        "seattle": {
            "front": 20,
            "rear": 25,
            "side": 5,
            "max_height": 30,
            "zone": "SF 5000",
        },
        "bellevue": {
            "front": 20,
            "rear": 20,
            "side": 15,
            "max_height": 35,
            "zone": "R-1",
        },
        "redmond": {
            "front": 15,
            "rear": 20,
            "side": 10,
            "max_height": 30,
            "zone": "R-4",
        },
        "bothell": {
            "front": 25,
            "rear": 25,
            "side": 8,
            "max_height": 35,
            "zone": "R 9600",
        },
    }
    return jsonify(db.get(city.lower(), db["seattle"]))


@app.route("/api/planning/chat", methods=["POST"])
def mock_planning_chat() -> Response:
    """
    Handle a mock chat interaction for the planning AI.

    Returns:
        Response: A JSON response containing the mock reply.
    """
    data: Dict[str, Any] = request.json or {}
    user_message: str = data.get("message", "").lower()

    if "bedroom" in user_message or "bed" in user_message:
        reply: str = (
            "Got it. I'll prioritize spatial allocation for the bedrooms. "
            "Do you want a primary suite with an attached bath?"
        )
    elif "kitchen" in user_message:
        reply = (
            "Noted. I'll configure an open-plan kitchen towards the social zones. "
            "Any preference on island size?"
        )
    else:
        reply = (
            "Understood. I am adding this constraint to the brief. "
            "Review the updated parameters when you're ready."
        )

    return jsonify({"reply": reply})


@app.route("/multifloor")
async def multifloor() -> Union[Response, str]:
    """
    Render the multi-floor workspace.

    Requires the 'Architect' role.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()

    if not client.isAuthenticated():
        return redirect(url_for("home"))
        
    role: Optional[str] = session.get("user_role")
    
    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
        
    return render_template("multifloor.html")


@app.route("/api/multifloor-image", methods=["POST"])
def multifloor_image() -> Response:
    """
    Generate and retrieve a multi-floor PNG representation from a remote DXF API.

    Returns:
        Response: A Flask response containing the PNG image.
    """
    response: requests.Response = requests.post(
        "http://16.176.176.187:8001/api/v1/generate-multifloor",
        json={"session_id": "sim_session_001"},
    )

    data: Dict[str, Any] = response.json()
    dxf_bytes: bytes = base64.b64decode(data["dxf"]["content_base64"])

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp.write(dxf_bytes)
        dxf_path: str = tmp.name

    doc: ezdxf.document.Drawing = ezdxf.readfile(dxf_path)

    fig: Figure = Figure(figsize=(10, 10))
    ax = fig.add_axes([0, 0, 1, 1])

    context: RenderContext = RenderContext(doc)
    backend: MatplotlibBackend = MatplotlibBackend(ax)

    Frontend(context, backend).draw_layout(doc.modelspace())

    png: io.BytesIO = io.BytesIO()

    fig.savefig(png, format="png", bbox_inches="tight")
    png.seek(0)

    return send_file(png, mimetype="image/png")


@app.route("/api/multifloor-dxf", methods=["POST"])
def multifloor_dxf() -> Response:
    """
    Generate and retrieve a multi-floor DXF file from a remote API.

    Returns:
        Response: A Flask response providing the DXF attachment for download.
    """
    response: requests.Response = requests.post(
        "http://16.176.176.187:8001/api/v1/generate-multifloor",
        json={"session_id": "sim_session_001"},
    )

    data: Dict[str, Any] = response.json()
    dxf_bytes: bytes = base64.b64decode(data["dxf"]["content_base64"])

    dxf_file: io.BytesIO = io.BytesIO(dxf_bytes)

    return send_file(
        dxf_file,
        mimetype="application/dxf",
        as_attachment=True,
        download_name="multifloor.dxf",
    )


@app.route("/outside-view")
async def outside_view() -> Union[Response, str]:
    """
    Render the exterior/outside view workspace.

    Requires the 'Architect' role.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))
        
    role: Optional[str] = session.get("user_role")
    if not role:
        return redirect(url_for("complete_profile"))
    if role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Architect":
        return redirect(url_for("in_progress"))
        
    return render_template("outside_view.html")


@app.route("/complete-profile", methods=["GET", "POST"])
async def complete_profile() -> Union[Response, str]:
    """
    Handle the profile completion step for newly authenticated users.

    Captures user's full name and role, stores it in Supabase, and updates
    the Flask session appropriately.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    email: Optional[str] = session.get("user_email")
    user_id: Optional[str] = session.get("user_id")

    if request.method == "POST":
        full_name: Optional[str] = request.form.get("full_name")
        role: Optional[str] = request.form.get("role")

        if user_id:
            now_iso: str = datetime.now(timezone.utc).isoformat()

            # Insert/upsert new user profile into Supabase according to new schema
            try:
                supabase.table("users").upsert(
                    {
                        "user_id": user_id,
                        "email": email,
                        "name": full_name,
                        "last_login": now_iso
                        # Notice: "role" is omitted here to prevent a crash, as it is no longer
                        # in the database schema. The app will persist it via the session below.
                    }
                ).execute()
            except Exception as e:
                print(f"Failed to upsert user profile: {e}")

        # Maintain application logic by setting the role in the Flask session
        if role:
            session["user_role"] = role

            if role == "Architect":
                return redirect(url_for("dashboard"))
            elif role == "User":
                return redirect(url_for("user_dashboard"))
            elif role == "Reviewer":
                return redirect(url_for("reviewer_dashboard"))
            else:
                return redirect(url_for("in_progress"))

    return render_template("complete_profile.html", email=email)


@app.route("/in-progress")
async def in_progress() -> Union[Response, str]:
    """
    Render a fallback 'In Progress' page.

    Handles edge-case roles or users without specific dashboards.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    # Optional: ensure specific roles aren't accidentally trapped here
    role: Optional[str] = session.get("user_role")
    if role == "Architect":
        return redirect(url_for("dashboard"))
    elif role == "User":
        return redirect(url_for("user_dashboard"))
    elif role == "Reviewer":
        return redirect(url_for("reviewer_dashboard"))

    return render_template("in_progress.html")


@app.route("/user-dashboard")
async def user_dashboard() -> Union[Response, str]:
    """
    Render the Homeowner / User dashboard.

    Requires the 'User' role. Fetches user data from Supabase.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    # --- USER ROLE CHECK ---
    role: Optional[str] = session.get("user_role")
    user_id: Optional[str] = session.get("user_id")

    if not role:
        return redirect(url_for("complete_profile"))
    if role == "Architect":
        return redirect(url_for("dashboard"))
    elif role == "Reviewer":
        return redirect(url_for("reviewer_dashboard"))
    elif role != "User":
        return redirect(url_for("in_progress"))
    # -----------------------

    # Initialize default user data
    user_data: Dict[str, str] = {
        "name": "Homeowner",
        "email": session.get("user_email") or "No email provided",
    }

    # Fetch the actual name from Supabase
    if user_id:
        try:
            response = (
                supabase.table("users").select("name").eq("user_id", user_id).execute()
            )
            if response.data and len(response.data) > 0:
                user_data["name"] = response.data[0].get("name") or "Homeowner"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    return render_template("user_dashboard.html", user=user_data)


@app.route("/reviewer/dashboard")
async def reviewer_dashboard() -> Union[Response, str]:
    """
    Render the Reviewer dashboard.

    Requires the 'Reviewer' role. Fetches user data from Supabase.

    Returns:
        Union[Response, str]: Redirect response or HTML content.
    """
    client: LogtoClient = get_logto_client()
    if not client.isAuthenticated():
        return redirect(url_for("home"))

    # --- REVIEWER ROLE CHECK ---
    role: Optional[str] = session.get("user_role")
    user_id: Optional[str] = session.get("user_id")

    if not role:
        return redirect(url_for("complete_profile"))
    if role == "Architect":
        return redirect(url_for("dashboard"))
    elif role == "User":
        return redirect(url_for("user_dashboard"))
    elif role != "Reviewer":
        return redirect(url_for("in_progress"))
    # -----------------------

    # Initialize default user data
    user_data: Dict[str, str] = {
        "name": "Reviewer",
        "email": session.get("user_email") or "No email provided",
    }

    # Fetch the actual name from Supabase
    if user_id:
        try:
            response = (
                supabase.table("users").select("name").eq("user_id", user_id).execute()
            )
            if response.data and len(response.data) > 0:
                user_data["name"] = response.data[0].get("name") or "Reviewer"
        except Exception as e:
            print(f"Failed to fetch user from Supabase: {e}")

    return render_template("reviewer_dashboard.html", user=user_data)


if __name__ == "__main__":
    app.run(debug=True)