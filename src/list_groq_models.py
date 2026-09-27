"""Diagnostic: lists every model your Groq key has access to."""
import os
from dotenv import load_dotenv
from openai import OpenAI
from config import ROOT

load_dotenv(ROOT / ".env")
key = os.getenv("GROQ_API_KEY")
print("Key loaded:", repr(key[:8] + "..." if key else None))

client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
for m in client.models.list().data:
    print(m.id)