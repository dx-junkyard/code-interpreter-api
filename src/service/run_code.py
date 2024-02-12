from src.config.logger import logger


def run_code(script: str):
    try:
        exec(script, {})
        return "コードの実行に成功しました。"
    except Exception as e:
        logger.error(f"Error: {e}")
        return "コードの実行に失敗しました。Error: " + str(e)
