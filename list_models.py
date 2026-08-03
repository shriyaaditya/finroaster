import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    print("Listing models with google-generativeai:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print("Error listing google-generativeai:", e)

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    print("\nListing models with google-genai:")
    for m in client.models.list():
        print(m.name)
except Exception as e:
    print("Error listing google-genai:", e)
