import json
import os
import time
import tomllib
from datetime import datetime
from logging import getLogger
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AzureOpenAI

logger = getLogger("uvicorn.app")

load_dotenv()

app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_endpoint = os.getenv("OPENAI_URI")
api_key = os.getenv("OPENAI_KEY")
api_version = os.getenv("OPENAI_VERSION")
api_deployment_name = os.getenv("OPENAI_GPT_DEPLOYMENT")

# pyproject.tomlファイルのパス
file_path = 'pyproject.toml'

# tomlファイルを読み込む
with open(file_path, 'rb') as toml_file:
    data = tomllib.load(toml_file)

# バージョン情報を取得
version = data['tool']['poetry']['version']

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=api_endpoint,
)

assistant = client.beta.assistants.create(
    name="Opendata Bridge",
    instructions="You are a specialist in extracting tables from various files such as PDF/Excel/csv and converting them into csv files.",
    tools=[
        {"type": "code_interpreter"}
    ],
    model=api_deployment_name,
)

user_database = {}


@app.post("/chat")
def chat(
        message: Annotated[str, Form()],
        user_id: Annotated[str, Form()],
        is_first: Annotated[bool, Form()],
):
    # If the user_id is not in the database, create a new thread
    if user_id not in user_database:
        user_database[user_id] = client.beta.threads.create().id
    # If the user_id is in the database and is the first message,
    # delete the thread and create a new thread
    elif is_first and user_id in user_database:
        client.beta.threads.delete(user_database[user_id])
        user_database[user_id] = client.beta.threads.create().id

    thread_id = user_database[user_id]

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message)

    content = chat_service(thread_id, user_id, message)

    return StreamingResponse(content, media_type="text/event-stream")


@app.post("/chat-with-file")
def chat_with_file(
        file: Annotated[bytes, File()],
        message: Annotated[str, Form()],
        user_id: Annotated[str, Form()],
        is_first: Annotated[bool, Form()],
):
    upload_file = client.files.create(
        file=file,
        purpose='assistants'
    )

    # If the user_id is not in the database, create a new thread
    if user_id not in user_database:
        user_database[user_id] = client.beta.threads.create().id
    # If the user_id is in the database and is the first message,
    # delete the thread and create a new thread
    elif is_first:
        client.beta.threads.delete(user_database[user_id])
        user_database[user_id] = client.beta.threads.create().id

    thread_id = user_database[user_id]
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message,
        file_ids=[upload_file.id])

    content = chat_service(thread_id, user_id, message)

    return StreamingResponse(content, media_type="text/event-stream")


@app.get("/download/{file_id}")
def download_file(
        file_id: str,
):
    try:
        write_file_data = client.files.content(file_id)
        file_data_bytes = write_file_data.read()
        # ファイルを返す
        return StreamingResponse([file_data_bytes], media_type="application/octet-stream")
    except Exception as e:
        # エラーが発生した場合500エラーを返す
        logger.error(e)
        raise HTTPException(status_code=500, detail="Undefined error")


def background_task(temp: str):
    if os.path.exists(temp):
        os.remove(temp)


def chat_service(thread_id, user_id, message):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant.id,
        instructions=f"Please address the user as '{user_id}'."
                     # 一番最初のメッセージにはシステムバージョンを含めることを指示する
                     + "Please include the system version in the first message. "
                     + f"Your system version : {version}. "
                     + "Be assertive, accurate, and polite. "
                     + "Ask if the user has further questions. "
                     + "Please respond in Japanese except for the user name. "
                     + "Should include the python code you executed in your response. "
                     + f"The current date and time is: {datetime.now().strftime("%x %X")}. "
    )

    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run.status == "completed":
            # Handle completed
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            item = messages.data[0].content[0].text
            result = item.value
            if (len(item.annotations) > 0) and (item.annotations[0].file_path.file_id is not None):
                # Retrieve file from file id
                file_id = item.annotations[0].file_path.file_id
            else:
                file_id = None
            break
        if run.status == "failed":
            result = f"Failed. Please try again."
            file_id = None
            break
        if run.status == "expired":
            # Handle expired
            result = "Expired. Please try again."
            file_id = None
            break
        if run.status == "cancelled":
            # Handle cancelled
            result = "Cancelled. Please try again."
            file_id = None
            break
        if run.status == "requires_action":
            # Handle function calling and continue processing
            pass
        else:
            time.sleep(5)

    content = [
        f"data: {json.dumps({"message": result})}\n",
    ]

    if file_id is not None:
        content.append(f"data: {json.dumps({'file_id': file_id})}\n")

    return content


@app.on_event("shutdown")
def shutdown_event():
    for user_id in user_database:
        thread_id = user_database[user_id]
        logger.info(client.beta.threads.delete(thread_id))
        logger.info(f"Thread {thread_id} deleted.")

    client.beta.assistants.delete(assistant.id)
    logger.info(f"Assistant {assistant.id} deleted.")
    logger.info("Shutdown completed.")
