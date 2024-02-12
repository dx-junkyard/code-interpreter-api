import json
import time
from typing import Dict, Any

from src.config.logger import logger
from src.repository.azure_open_ai_client import azure_open_ai_client
from src.repository.user_repository import upsert_file


def chat_service(
        user_id: str,
        thread_id: str,
        assistant_id: str,
        instruction: str,
        available_functions: Dict[str, Any],
):
    run = azure_open_ai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions=instruction,
    )

    while True:
        run = azure_open_ai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        logger.info(f"run status: {run.status}")

        if run.status == "completed":
            # Handle completed
            messages = azure_open_ai_client.beta.threads.messages.list(thread_id=thread_id)
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
            tool_responses = []
            if (
                    run.required_action.type == "submit_tool_outputs"
                    and run.required_action.submit_tool_outputs.tool_calls is not None
            ):
                tool_calls = run.required_action.submit_tool_outputs.tool_calls

                for call in tool_calls:
                    if call.type == "function":
                        if call.function.name not in available_functions:
                            raise Exception("Function requested by the model does not exist")
                        function_to_call = available_functions[call.function.name]
                        tool_response = function_to_call(**json.loads(call.function.arguments))
                        tool_responses.append({"tool_call_id": call.id, "output": tool_response})

            run = azure_open_ai_client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_responses
            )
        else:
            time.sleep(5)

    obj = json.dumps({"message": result})

    content = [
        f"data: {obj}\n",
    ]

    if file_id is not None:
        obj = json.dumps({'file_id': file_id})
        upsert_file(user_id, file_id, azure_open_ai_client.files.content(file_id).read())
        content.append(f"data: {obj}\n")

    return content
