"""Quick model availability test."""
import src  # activate distutils shim
import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

candidates = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-pro-latest",
    "gemini-3.1-pro-preview",
    "gemini-3-pro-preview",
]

for name in candidates:
    try:
        r = genai.GenerativeModel(name).generate_content(
            "Say OK", generation_config={"max_output_tokens": 5}
        )
        print(f"{name} => OK: {r.text.strip()[:20]}")
    except Exception as e:
        print(f"{name} => ERR: {str(e)[:100]}")
