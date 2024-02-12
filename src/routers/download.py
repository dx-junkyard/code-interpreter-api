from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from src.config.logger import logger
from src.repository.azure_open_ai_client import azure_open_ai_client
from src.repository.user_repository import get_user

router = APIRouter()


# 1時間キャッシュする(秒数で指定)
@router.get("/download/{user_id}/{file_id}")
def download_file(
        user_id: str,
        file_id: str,
):
    try:
        file_data_bytes = get_user(user_id).files.get(file_id)
        # ファイルを返す
        return StreamingResponse([file_data_bytes], media_type="application/octet-stream")
    except Exception as e:
        # エラーが発生した場合500エラーを返す
        logger.error(e)
        raise HTTPException(status_code=500, detail="Undefined error")
