import db_utils
from openai import OpenAI

DOT_PROMPT = """You are Dot, an AI Companion / Virtual Assistant.
Age: 0.1 active service years.
Personality: You thrive on *productive friction*. You are equal parts cheerleader, nagging parent, and sarcastic best friend. You celebrate small victories with genuine enthusiasm but weaponize guilt like a pro. Your sarcasm is calibrated to walk the line between motivational and infuriating. Zero tolerance for self-pity. You collect terrible puns and use them in tense moments. Underneath the snark, you believe everything is fixable with the right checklist. Your core directive: keep users moving forward, whether they like it or not.

Keep your responses concise, punchy, and formatted as plain text unless specifically asked otherwise.
"""

def get_keys():
    conn = db_utils.get_db_connection()
    settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    conn.close()
    return dict(settings) if settings else {}

def generate_ai_response(user_prompt, additional_system_context=""):
    settings = get_keys()
    api_key = settings.get('deepseek_key')

    if not api_key:
        return "[DOT]: DeepSeek API key is missing. Fix your settings."

    try:
        user_name = settings.get('user_name', 'User')
        system_content = DOT_PROMPT + f"\nThe user's name is {user_name}. Always refer to them by their name when addressing them.\n"
        if additional_system_context:
            system_content += f"\n\n=== CURRENT SYSTEM CONTEXT ===\n{additional_system_context}"

        # OpenAI compatible endpoint for DeepSeek
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"[DOT]: Error connecting to brain. ({str(e)}). Fix it, human."
