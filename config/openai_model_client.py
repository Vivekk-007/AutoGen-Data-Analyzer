from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os

load_dotenv()


def get_model_client():
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        return OpenAIChatCompletionClient(
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "family": "llama",
                "structured_output": True,
            },
        )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        return OpenAIChatCompletionClient(
            model="gemini-2.5-flash",
            api_key=gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "family": "gemini",
                "structured_output": True,
            },
        )

    raise RuntimeError("No API key found. Set GROQ_API_KEY or GEMINI_API_KEY in the .env file.")