FROM --platform=linux/x86_64 python:3.11.3
WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./pyproject.toml /code/pyproject.toml

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 必要なツールをインストール
RUN apt-get update && apt-get install -y nkf && apt-get install -y default-jdk

COPY ./src /code/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]
