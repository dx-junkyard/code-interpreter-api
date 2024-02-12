from openai import AzureOpenAI
from src.config.azure_open_ai_settings import azure_open_ai_settings


def get_azure_open_ai_client():

    client = AzureOpenAI(
        api_key=azure_open_ai_settings.API_KEY,
        api_version=azure_open_ai_settings.API_VERSION,
        azure_endpoint=azure_open_ai_settings.API_ENDPOINT,
    )

    return client


azure_open_ai_client = get_azure_open_ai_client()
