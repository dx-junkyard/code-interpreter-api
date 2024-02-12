from typing import Dict, List

from src.model.user import User

user_database: Dict[str, User] = {}


def upsert_thread(user_id: str, thread_id: str) -> None:

    if user_id in user_database:
        user_database[user_id].thread = thread_id
    else:
        user_database[user_id] = User(name=user_id, thread=thread_id)


def upsert_file(user_id: str, file_id, content: bytes) -> None:
    if user_id in user_database:
        user_database[user_id].files[file_id] = content
    else:
        user_database[user_id] = User(name=user_id, files={file_id: content})


def get_user(user_id: str) -> User:
    return user_database[user_id]




def exist_thread(user_id: str) -> bool:
    return user_id in user_database and user_database[user_id].thread is not None


def get_all_thread() -> List[str]:
    return [user.thread for user in user_database.values() if user.thread is not None]
