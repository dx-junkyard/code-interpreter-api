from fastapi import APIRouter

from src.config.logger import logger
from src.repository.azure_open_ai_client import azure_open_ai_client
from src.repository.user_repository import get_all_thread

router = APIRouter()


@router.on_event("shutdown")
def shutdown_event():
    for thread_id in get_all_thread():
        logger.info(azure_open_ai_client.beta.threads.delete(thread_id))
        logger.info(f"Thread {thread_id} deleted.")

    # azure_open_ai_client.beta.assistants.delete(opendata_bridge_chat_assistant.id)
    # azure_open_ai_client.beta.assistants.delete(opendata_bridge_runner_assistant.id)

    logger.info(f"All Assistant deleted.")
    logger.info("Shutdown completed.")
