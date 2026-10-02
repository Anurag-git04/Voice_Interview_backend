"""Quick script to check available Groq models."""
from groq import Groq
from app.config import settings

client = Groq(api_key=settings.groq_api_key)

print("Available models from your Groq API key:\n")
print("-" * 60)

try:
    models = client.models.list()
    for model in models.data:
        print(f"ID: {model.id}")
        if hasattr(model, 'owned_by'):
            print(f"   Owner: {model.owned_by}")
        print()
except Exception as e:
    print(f"Error listing models: {e}")
