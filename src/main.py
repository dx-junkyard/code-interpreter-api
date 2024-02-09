import os
import time
from datetime import datetime
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Response, File, Form, HTTPException
from openai import AzureOpenAI

load_dotenv()

app = FastAPI()

api_endpoint = os.getenv("OPENAI_URI")
api_key = os.getenv("OPENAI_KEY")
api_version = os.getenv("OPENAI_VERSION")
api_deployment_name = os.getenv("OPENAI_GPT_DEPLOYMENT")
api_assistant_id = os.getenv("OPENAI_GPT_ASSISTANT_ID")

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=api_endpoint,
)

user_database = {}


@app.post("/chat")
def chat(
        message: str,
        user_id: str,
):
    # If the user_id is not in the database, create a new thread
    if user_id not in user_database:
        user_database[user_id] = client.beta.threads.create().id

    thread_id = user_database[user_id]
    return chat_service(thread_id, user_id, message)


@app.post("/chat-with-file")
def chat_with_file(
        file: Annotated[bytes, File()],
        message: Annotated[str, Form()],
        user_id: Annotated[str, Form()],
):
    upload_file = client.files.create(
        file=file,
        purpose='assistants'
    )

    # If the user_id is not in the database, create a new thread
    if user_id not in user_database:
        user_database[user_id] = client.beta.threads.create().id

    thread_id = user_database[user_id]
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message,
        file_ids=[upload_file.id])

    return chat_service(thread_id, user_id, message)


@app.get("/download/{file_id}")
def download_file(
        file_id: str,
):
    try:
        write_file_data = client.files.content(file_id)
        file_data_bytes = write_file_data.read()
        # ファイルを返す
        return Response(content=file_data_bytes)
    except Exception as e:
        # エラーが発生した場合500エラーを返す
        print(e)
        raise HTTPException(status_code=500, detail="Undefined error")


@app.delete("/delete/{user_id}")
def delete_session(
        user_id: str,
):
    thread_id = user_database[user_id]

    # If the user_id is not in the database, create a new thread
    try:
        print(client.beta.threads.delete(thread_id))
        result = "Thread deleted."
        if user_id in user_database:
            user_database.pop(user_id)
        else:
            print("Thread not found in database.")
    except Exception as e:
        print(e)
        result = "Failed to delete thread."

    return {"message": result, "thread_id": thread_id}


def chat_service(thread_id, user_id, message):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=api_assistant_id,
        instructions=f"Please address the user as {user_id}."
                     + "The user has a premium account. "
                     + "Be assertive, accurate, and polite. "
                     + "Ask if the user has further questions. "
                     + "The current date and time is: "
                     + datetime.now().strftime("%x %X")
                     + ". ",
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
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            answer = messages.data[0].content[0].text.value
            result = f"Failed User:\n{message}\nAssistant:\n{answer}\n"
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

    return {"message": result, "thread_id": thread_id, "file_id": file_id}