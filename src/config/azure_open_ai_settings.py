import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class AzureOpenAiSettings(BaseSettings):
    API_ENDPOINT: str = os.getenv("OPENAI_URI")
    API_KEY: str = os.getenv("OPENAI_KEY")
    API_VERSION: str = os.getenv("OPENAI_VERSION")
    API_DEPLOYMENT_NAME: str = os.getenv("OPENAI_GPT_DEPLOYMENT")
    OPENDATA_BRIDGE_CHAT_ASSISTANT_ID: str = os.getenv("OPENDATA_BRIDGE_CHAT_ASSISTANT_ID")
    OPENDATA_BRIDGE_RUNNER_ASSISTANT_ID: str = os.getenv("OPENDATA_BRIDGE_RUNNER_ASSISTANT_ID")


azure_open_ai_settings = AzureOpenAiSettings()
