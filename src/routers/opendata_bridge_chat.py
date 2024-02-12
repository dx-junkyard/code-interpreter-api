from datetime import datetime
from typing import Annotated

from fastapi import File, Form, APIRouter
from fastapi.responses import StreamingResponse

from src.config.azure_open_ai_settings import azure_open_ai_settings
from src.config.tool_version_config import tool_version
from src.repository.azure_open_ai_client import azure_open_ai_client
from src.repository.user_repository import upsert_thread, get_user, exist_thread
from src.service.chat_assistant import chat_service


# Dependency
def update_assistant(azure_open_ai_azure_open_ai_client, assistant_id):
    return azure_open_ai_azure_open_ai_client.beta.assistants.update(
        assistant_id,
        name="Opendata Bridge Chat",
        instructions="You are a specialist in extracting tables from various files such as PDF/Excel/csv and converting them into csv files.",
        tools=[
            {"type": "code_interpreter"}
        ],
        model=azure_open_ai_settings.API_DEPLOYMENT_NAME
    )


opendata_bridge_chat_assistant = update_assistant(
    azure_open_ai_client,
    azure_open_ai_settings.OPENDATA_BRIDGE_CHAT_ASSISTANT_ID)

router = APIRouter(prefix="/opendata-bridge-chat")


@router.post("/chat")
def chat(
        message: Annotated[str, Form()],
        user_id: Annotated[str, Form()],
        is_first: Annotated[bool, Form()],
):
    # If the user_id is not in the database, create a new thread
    if exist_thread(user_id) is False:
        upsert_thread(user_id, azure_open_ai_client.beta.threads.create().id)
    # If the user_id is in the database and is the first message,
    # delete the thread and create a new thread
    elif is_first and exist_thread(user_id):
        azure_open_ai_client.beta.threads.delete(get_user(user_id).thread)
        upsert_thread(user_id, azure_open_ai_client.beta.threads.create().id)

    thread_id = get_user(user_id).thread

    azure_open_ai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message)

    content = chat_service(user_id, thread_id, opendata_bridge_chat_assistant.id, get_instruction(user_id), {})

    return StreamingResponse(content, media_type="text/event-stream")


@router.post("/chat/file")
def chat_with_file(
        file: Annotated[bytes, File()],
        message: Annotated[str, Form()],
        user_id: Annotated[str, Form()],
        is_first: Annotated[bool, Form()],
):
    upload_file = azure_open_ai_client.files.create(
        file=file,
        purpose='assistants'
    )

    # If the user_id is not in the database, create a new thread
    if exist_thread(user_id) is False:
        upsert_thread(user_id, azure_open_ai_client.beta.threads.create().id)
    # If the user_id is in the database and is the first message,
    # delete the thread and create a new thread
    elif is_first and exist_thread(user_id):
        azure_open_ai_client.beta.threads.delete(get_user(user_id).thread)
        upsert_thread(user_id, azure_open_ai_client.beta.threads.create().id)

    thread_id = get_user(user_id).thread
    azure_open_ai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message,
        file_ids=[upload_file.id])

    content = chat_service(user_id, thread_id, opendata_bridge_chat_assistant.id, get_instruction(user_id), {})

    return StreamingResponse(content, media_type="text/event-stream")


def get_instruction(
        user_id,
):
    return f"Please address the user as '{user_id}'. " \
           f"Your system version : {tool_version}. " \
           "Be assertive, accurate, and polite. " \
           "Ask if the user has further questions. " \
           "Please respond in Japanese except for the user name. " \
           "Should include the python code you executed in your response. " \
           f"The current date and time is: {datetime.now().strftime('%x %X')}. "
