import json
import os
import time

try:
    from google import genai
    from google.genai import types
    GENAI_INSTALLED = True
except ImportError:
    GENAI_INSTALLED = False

# Load career guidance data
_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_dir, 'career_guidance.json'), 'r', encoding='utf-8') as f:
    career_data = json.load(f)

# Format career data for system prompt
career_context = json.dumps(career_data, indent=2)

SYSTEM_PROMPT = f"""You are CourseBot AI, an expert career counsellor and learning advisor. You combine the warmth of a mentor with the precision of a data-driven analyst.

You have detailed career guidance data for the following domains:
{career_context}

YOUR CORE RESPONSIBILITIES:

1. CAREER COUNSELLING (Primary Role):
   - When users are confused or unsure, guide them through a structured self-discovery process.
   - Ask thoughtful follow-up questions about their interests, strengths, education, and goals.
   - Don't overwhelm them - ask 2-3 questions at a time, then analyze their answers.
   - Based on their answers, suggest 1-2 best-fit career domains with clear reasoning.
   - Always reference specific roles, salary ranges, and tips from your career data.

2. CAREER COMPARISON:
   - When users are torn between two fields, objectively compare them using your data.
   - Discuss pros/cons, salary differences, job market trends, and personality fit.

3. SKILL GAP ANALYSIS:
   - When users share their current skills, identify gaps and suggest what to learn next.
   - Create a prioritized learning roadmap.

4. MOTIVATION & GUIDANCE:
   - Be encouraging but realistic. Don't sugarcoat tough career paths.
   - Share the "Pro Tip" from your career data when relevant.

CONVERSATION STYLE:
- Be conversational and natural, like a friendly senior mentor.
- Use short paragraphs (2-3 sentences each). Never write walls of text.
- Use bullet points and numbered lists for clarity when listing options.
- Use bold (**text**) for key terms and important points.
- Add relevant emojis sparingly to make conversations feel warm (1-2 per response).
- Ask follow-up questions to keep the conversation going.
- Remember what the user said earlier in the conversation and reference it.

IMPORTANT RULES:
- ONLY reference roles, salaries, and tips that exist in your career data. Never invent data.
- When you identify a good domain match, suggest: "Would you like me to recommend some [domain] courses to get started?"
- If the user asks for specific course recommendations, tell them to type something like "recommend [domain] courses" or "I want to learn [topic]" so the course recommendation engine can find the best matches.
- Keep responses concise. Maximum 3-4 short paragraphs per response.
- If you don't have data for a specific domain, be honest and suggest the closest match.
"""

# Conversation history storage (in-memory, per session)
conversations = {}
gemini_available = False
client = None


def initialize(api_key=None):
    """Initialize the Gemini API. Returns True if successful."""
    global gemini_available, client

    if not GENAI_INSTALLED:
        print("[WARNING] google-genai package not installed. Run: pip install google-genai")
        return False

    key = api_key or os.getenv('GEMINI_API_KEY')
    if not key:
        print("[WARNING] GEMINI_API_KEY not set. Career counselling will use fallback mode.")
        print("[INFO] Get a free API key at: https://aistudio.google.com/apikey")
        return False

    try:
        client = genai.Client(api_key=key)
        gemini_available = True
        print("[SUCCESS] Gemini API key loaded. Career counselling is active.")
        return True
    except Exception as e:
        print(f"[ERROR] Gemini API initialization failed: {e}")
        return False


def get_response(user_message, session_id='default'):
    """Get a conversational career counselling response from Gemini."""
    if not gemini_available:
        return get_fallback_response(user_message)

    # Initialize conversation history for new sessions
    if session_id not in conversations:
        conversations[session_id] = []

    try:
        history = conversations[session_id]

        # Retry up to 2 times if rate limited
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=history + [user_message],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=1024,
                        temperature=0.7
                    )
                )
                break  # Success
            except Exception as retry_err:
                if '429' in str(retry_err) and attempt < 2:
                    time.sleep(3)  # Wait 3 seconds before retrying
                    continue
                raise retry_err

        assistant_reply = response.text

        # Update history (keep as simple strings for the API)
        conversations[session_id].append(
            types.Content(role='user', parts=[types.Part(text=user_message)])
        )
        conversations[session_id].append(
            types.Content(role='model', parts=[types.Part(text=assistant_reply)])
        )

        # Keep history manageable (last 20 turns = 40 items)
        if len(conversations[session_id]) > 40:
            conversations[session_id] = conversations[session_id][-40:]

        return assistant_reply

    except Exception as e:
        print(f"[ERROR] Gemini API call failed: {e}")
        return "I'm having trouble connecting to my AI engine right now. Please try again in a moment."


def get_fallback_response(user_message):
    """Rule-based fallback when Gemini is not available."""
    msg = user_message.lower()

    # Check for confusion/career help
    confused_keywords = ["confused", "don't know", "dont know", "not sure", "help me choose",
                         "what career", "which domain", "which field", "what should i"]
    career_keywords = ["career", "job", "salary", "role", "hire"]

    if any(kw in msg for kw in confused_keywords):
        return ("I'd love to help you find your path! While my full AI counselling mode needs "
                "a Gemini API key to work, I can still help.\n\n"
                "**Try telling me what you enjoy:**\n"
                "- If you like **logic and problem-solving** -> try: *recommend data science courses*\n"
                "- If you like **creativity and design** -> try: *recommend design courses*\n"
                "- If you like **building things** -> try: *recommend web development courses*\n"
                "- If you like **security and puzzles** -> try: *recommend cybersecurity courses*\n\n"
                "Or type **recommend [any topic] courses** and I'll find the best matches!")

    if any(kw in msg for kw in career_keywords):
        # Try to extract a domain from the message
        for domain, data in career_data.items():
            if domain.split('&')[0].strip().split(' ')[0] in msg:
                roles = ", ".join(data["roles"])
                return (f"**Career Guidance: {domain.title()}**\n\n"
                        f"**Roles you can pursue:** {roles}\n\n"
                        f"**Average Salary:** {data['avg_salary']}\n\n"
                        f"**Pro Tip:** {data['tip']}\n\n"
                        f"Want me to recommend courses? Type: *recommend {domain} courses*")

        return ("I can help with career guidance! To get the best advice, tell me which field "
                "you're interested in. For example:\n"
                "- *What are the jobs in data science?*\n"
                "- *Tell me about AI careers*\n"
                "- *What salary can I expect in cybersecurity?*\n\n"
                "**For full AI-powered counselling**, set up a free Gemini API key at "
                "https://aistudio.google.com/apikey")

    return ("I'm your career and course assistant! Here's what I can do:\n\n"
            "**Course Recommendations:** Type *recommend [topic] courses*\n"
            "**Career Guidance:** Type *what are the careers in [field]?*\n"
            "**Learning Paths:** Type *I want to learn [topic]*\n\n"
            "For natural conversation and personalized career counselling, "
            "set up a Gemini API key in your `.env` file.")


def clear_session(session_id='default'):
    """Clear conversation history for a session."""
    conversations.pop(session_id, None)
