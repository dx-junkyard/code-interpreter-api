import json
import os
import uuid
from typing import Annotated

from fastapi import File, Form, APIRouter, BackgroundTasks
from starlette.responses import StreamingResponse

from src.config.azure_open_ai_settings import azure_open_ai_settings
from src.repository.azure_open_ai_client import azure_open_ai_client
from src.repository.user_repository import upsert_file
from src.service.chat_assistant import chat_service
from src.service.run_code import run_code


def get_prompt(filename: str, script: str):
    return f"""
あなたはpandasなどのツールでデータの編集を行うpythonコードと編集対象のファイルを受け取りました。
それらを使って以下のタスクを実行してください。回答内容には各ステップの実行結果を表示してください。
各ステップの実行でユーザの確認は絶対にしないでください。構わず次々と実行してください。
作業方針の確認も不要です。全てのタスクを実行してください。
これを全て実行できなければ、罰金1億円のペナルティが発生します。

# タスク
(1)
サーバの情報にアクセスするようなコードが存在しないかチェックしてください。

(2) 
受け取ったファイル編集用のコードにファイルの入出力に関するコードがあれば、
入力ファイル名及び出力ファイル名を{filename}に変更してください。
pandasのto_csvの引数にはindex=Noneを指定してください。
それ以外のコードは絶対に変更してはいけません。
ファイルパスは絶対に指定してはいけません。例えば、/mnt/data/{filename}のような指定は絶対にしてはいけません。
指定した場合は、罰金が発生します。

(3)
format_file_jobでファイル編集を実行してください。
このフェーズを実行しなければ罰金が発生するので、絶対に実行してください。

(4) 
ファイル編集が終わったら、これまでのタスクの実行結果全てを表示してください。
===
{script}
"""


instruction = """
You are an assistant designed to help people answer questions.
"""


# Dependency
def update_assistant(azure_open_ai_azure_open_ai_client, assistant_id):
    return azure_open_ai_azure_open_ai_client.beta.assistants.update(
        assistant_id,
        name="Opendata Bridge Runner",
        instructions=instruction,
        tools=[
            {"type": "code_interpreter"},
            {
                "type": "function",
                "function": {
                    "name": "format_file_job",
                    "description": "ファイルの編集を行うジョブです",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script": {
                                "type": "string",
                                "description": "ファイル編集の内容が記述されたpythonコードを指定してください",
                            },
                        },
                        "required": [
                            "script"
                        ],
                    },
                },
            },
        ],
        model=azure_open_ai_settings.API_DEPLOYMENT_NAME
    )


available_functions = {
    "format_file_job": run_code
}

opendata_bridge_runner_assistant = update_assistant(
    azure_open_ai_client,
    azure_open_ai_settings.OPENDATA_BRIDGE_RUNNER_ASSISTANT_ID)

router = APIRouter(prefix="/opendata-bridge-runner")


@router.post("/run/file")
def run_file(
        file: Annotated[bytes, File()],
        user_id: Annotated[str, Form()],
        script: Annotated[str, Form()],
        background_tasks: BackgroundTasks
):
    # 一時的なファイル保存先の設定
    filename = f"{str(uuid.uuid4())}"

    with open(filename, "wb") as buffer:
        buffer.write(file)

    upload_file = azure_open_ai_client.files.create(
        file=file,
        purpose='assistants'
    )

    thread_id = azure_open_ai_client.beta.threads.create().id

    azure_open_ai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=get_prompt(filename, script),
        file_ids=[upload_file.id])

    content = chat_service(
        user_id,
        thread_id,
        opendata_bridge_runner_assistant.id,
        get_prompt(filename, script),
        available_functions)

    with open(filename, "rb") as buffer:
        output_binary = buffer.read()

    upsert_file(user_id, filename, output_binary)

    obj = json.dumps({'file_id': filename})
    content.append(f"data: {obj}\n")

    background_tasks.add_task(background_task, thread_id, filename)

    return StreamingResponse(content, media_type="text/event-stream")


def background_task(thread_id: str, filename: str):
    # delete thread
    azure_open_ai_client.beta.threads.delete(thread_id)
    if os.path.exists(filename):
        os.remove(filename)
