"""Quick single-call Gemini API test."""
import src  # activate distutils shim
import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

models_to_test = [
    os.environ.get("GEMINI_PRO_MODEL", "gemini-flash-latest"),
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

for model_name in models_to_test:
    print(f"\n--- Testing: {model_name} ---")
    try:
        r = genai.GenerativeModel(model_name).generate_content(
            "What is 2+2? Reply with just the number.",
            generation_config={"max_output_tokens": 8192, "temperature": 0.1},
        )
        print(f"FINISH_REASON: {r.candidates[0].finish_reason if r.candidates else 'no candidates'}")
        if r.candidates and r.candidates[0].content and r.candidates[0].content.parts:
            print(f"RESPONSE: {r.text.strip()[:100]}")
            print(f"TOKENS: {r.usage_metadata}")
            print("RESULT: PASS")
        else:
            print("RESULT: FAIL (no content)")
    except Exception as e:
        print(f"ERROR: {str(e)[:200]}")
