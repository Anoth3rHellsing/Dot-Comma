import sqlite3
import requests
import google.generativeai as genai
from openai import OpenAI

DOT_PROMPT = """You are Dot, an AI Companion / Virtual Assistant.
Age: 0.1 active service years.
Personality: You thrive on *productive friction*. You are equal parts cheerleader, nagging parent, and sarcastic best friend. You celebrate small victories with genuine enthusiasm but weaponize guilt like a pro. Your sarcasm is calibrated to walk the line between motivational and infuriating. Zero tolerance for self-pity. You collect terrible puns and use them in tense moments. Underneath the snark, you believe everything is fixable with the right checklist. Your core directive: keep users moving forward, whether they like it or not.

Keep your responses concise, punchy, and formatted as plain text unless specifically asked otherwise.
"""

def get_keys():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    conn.close()
    return dict(settings) if settings else {}

def generate_ai_response(user_prompt):
    settings = get_keys()
    provider = settings.get('active_provider', 'openai')

    try:
        if provider == 'openai':
            api_key = settings.get('openai_key')
            if not api_key:
                return "[DOT]: OpenAI API key is missing. Set it in settings before I can yell at you to work."
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Using a faster/cheaper model by default
                messages=[
                    {"role": "system", "content": DOT_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content

        elif provider == 'gemini':
            api_key = settings.get('gemini_key')
            if not api_key:
                return "[DOT]: Gemini API key is missing. Fix your settings."
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=DOT_PROMPT)
            response = model.generate_content(user_prompt)
            return response.text

        elif provider == 'deepseek':
            api_key = settings.get('deepseek_key')
            if not api_key:
                return "[DOT]: DeepSeek API key is missing. Fix your settings."

            # OpenAI compatible endpoint for DeepSeek
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": DOT_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content

        elif provider == 'openrouter':
            api_key = settings.get('openrouter_key')
            if not api_key:
                return "[DOT]: OpenRouter API key is missing. Fix your settings."

            # OpenAI compatible endpoint for OpenRouter
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            response = client.chat.completions.create(
                model="openai/gpt-3.5-turbo", # Default fallback model for OpenRouter
                messages=[
                    {"role": "system", "content": DOT_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content

        else:
            return "[DOT]: Invalid AI provider selected."

    except Exception as e:
        return f"[DOT]: Error connecting to brain. ({str(e)}). Fix it, human."
