import google.generativeai as genai
import os

os.environ["GEMINI_API_KEY"] = "AIzaSyBEmmuMA1dNa28-r7UWuTxWtUvHvCy5j34"
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

print("Available models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"- {model.name}")
