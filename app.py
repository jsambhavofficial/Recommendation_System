from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import pandas as pd
import os
from main import handle_conversational_intent, recommend_courses
import career_chat
import database as db

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, template_folder='.')
app.secret_key = os.getenv('SECRET_KEY', 'coursebot-secret-key-change-in-production')

# Initialize Gemini on startup
career_chat.initialize()


# ── AUTH ROUTES ──

@app.route('/')
@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect('/chatbot')
    return render_template('login.html')


@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('live.html')


@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({"success": False, "message": "All fields are required."}), 400
    if len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters."}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
    if '@' not in email or '.' not in email:
        return jsonify({"success": False, "message": "Enter a valid email address."}), 400

    success, message = db.create_user(username, email, password)
    status = 200 if success else 409
    return jsonify({"success": success, "message": message}), status


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')

    if not username_or_email or not password:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    success, result = db.authenticate_user(username_or_email, password)
    if success:
        session['user_id'] = result['id']
        session['username'] = result['username']
        return jsonify({"success": True, "message": "Login successful!", "user": result})
    else:
        return jsonify({"success": False, "message": result}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})


@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({"logged_in": False}), 401
    user = db.get_user_by_id(session['user_id'])
    if user:
        return jsonify({"logged_in": True, "user": user})
    return jsonify({"logged_in": False}), 401


# ── CHAT HISTORY ROUTES ──

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    if 'user_id' not in session:
        return jsonify([])
    sessions = db.get_user_sessions(session['user_id'])
    return jsonify(sessions)


@app.route('/api/sessions', methods=['POST'])
def create_chat_session():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.json or {}
    title = data.get('title', 'New Chat')
    session_id = db.create_session(session['user_id'], title)
    return jsonify({"session_id": session_id})


@app.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
def get_messages(session_id):
    messages = db.get_session_messages(session_id)
    return jsonify(messages)


@app.route('/api/sessions/<int:session_id>/messages', methods=['POST'])
def save_message(session_id):
    data = request.json
    role = data.get('role', 'user')
    content = data.get('content', '')
    msg_type = data.get('msg_type', 'chat')
    db.save_message(session_id, role, content, msg_type)
    return jsonify({"success": True})


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    success = db.delete_session(session_id, session['user_id'])
    return jsonify({"success": success})


@app.route('/api/sessions/all', methods=['DELETE'])
def delete_all_sessions():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    db.delete_all_sessions(session['user_id'])
    return jsonify({"success": True})


# ── HELPERS ──

def df_to_json(df):
    """Helper to convert Pandas DataFrame to list of dicts safely."""
    if df is None or df.empty:
        return []
    return df.where(pd.notnull(df), None).to_dict(orient='records')


def get_json_path(domain_data):
    """Convert domain learning path DataFrames to JSON."""
    json_path = {}
    if "path" in domain_data:
        for skill, df in domain_data["path"].items():
            json_path[skill] = df_to_json(df)
    return json_path


def is_course_query(query):
    """Detect if the user is asking for course recommendations (ML engine)."""
    q = query.lower()
    course_signals = ['course', 'courses', 'recommend', 'tutorial', 'certificate']
    learn_patterns = ['i want to learn', 'teach me', 'show me', 'help me learn',
                      'beginner course', 'intermediate course', 'advanced course']

    if any(s in q for s in course_signals):
        return True
    if any(p in q for p in learn_patterns):
        return True
    return False


def build_course_response(results):
    """Build the JSON response for course recommendations."""
    if not results:
        return jsonify({"status": "off_topic", "message": "No relevant courses found."})

    # Multiple domains
    if len(results) > 1:
        domains = list(results.keys())
        query_a = domains[0]
        query_b = domains[1]

        path_a = {
            "domain": query_a,
            "recommendations": df_to_json(results[query_a]["recommendations"]),
            "learning_path": get_json_path(results[query_a]),
            "guidance": results[query_a].get("guidance")
        }

        path_b = {
            "domain": query_b,
            "recommendations": df_to_json(results[query_b]["recommendations"]),
            "learning_path": get_json_path(results[query_b]),
            "guidance": results[query_b].get("guidance")
        }

        return jsonify({
            "status": "multi_domain",
            "query_a": query_a,
            "path_a": path_a,
            "query_b": query_b,
            "path_b": path_b
        })

    # Single domain
    domain_name = list(results.keys())[0]
    domain_data = results[domain_name]
    has_guidance = domain_data.get("guidance") is not None

    return jsonify({
        "status": "career" if has_guidance else "success",
        "domain": domain_name,
        "recommendations": df_to_json(domain_data["recommendations"]),
        "learning_path": get_json_path(domain_data),
        "guidance": domain_data.get("guidance")
    })


# ── MAIN CHAT ENDPOINT ──

@app.route('/chat', methods=['POST'])
def chat():
    """
    Unified smart endpoint. Routes internally:
      - Greetings/thanks -> handled locally
      - Course queries    -> ML engine (LinearSVC + TF-IDF)
      - Career/general    -> Gemini API (or fallback)
    """
    data = request.json
    query = data.get('query', '')
    gemini_session_id = data.get('session_id', 'default')
    chat_session_id = data.get('chat_session_id')

    # Save user message to DB if session exists
    if chat_session_id and 'user_id' in session:
        db.save_message(chat_session_id, 'user', query, 'chat')

    # 1. Check for simple greetings (no API call needed)
    conv_response = handle_conversational_intent(query)
    if conv_response:
        if chat_session_id and 'user_id' in session:
            db.save_message(chat_session_id, 'bot', conv_response, 'greeting')
        return jsonify({"status": "greeting", "message": conv_response})

    # 2. Check if this is a course-specific query -> ML engine
    if is_course_query(query):
        results = recommend_courses(query)
        response = build_course_response(results)
        if chat_session_id and 'user_id' in session:
            db.save_message(chat_session_id, 'bot', query, 'course')
        return response

    # 3. Everything else -> Gemini career counselling
    try:
        response = career_chat.get_response(query, gemini_session_id)
        if chat_session_id and 'user_id' in session:
            db.save_message(chat_session_id, 'bot', response, 'chat')
        return jsonify({"status": "chat", "message": response})
    except Exception as e:
        print(f"[ERROR] Chat failed: {e}")
        return jsonify({"status": "chat", "message": "Sorry, something went wrong. Please try again."})


# Keep /recommend as a backward-compatible endpoint
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json
    query = data.get('query', '')

    conv_response = handle_conversational_intent(query)
    if conv_response:
        return jsonify({"status": "greeting", "message": conv_response})

    results = recommend_courses(query)
    return build_course_response(results)


@app.route('/clear_session', methods=['POST'])
def clear_session():
    """Clear conversation history for a session."""
    data = request.json
    gemini_session_id = data.get('session_id', 'default')
    career_chat.clear_session(gemini_session_id)
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    print("[SUCCESS] CourseBot AI API is starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
