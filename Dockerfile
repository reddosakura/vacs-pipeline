FROM python:3.12.7-alpine
LABEL authors="reddosakura"

WORKDIR /sudp_app

COPY requirements.txt .

RUN apk add --update --no-cache --virtual .tmp-build-deps \
    gcc libc-dev linux-headers postgresql-dev \
    && apk add libffi-dev

RUN python3 -m venv .venv

RUN pip install -r requirements.txt

COPY venv/.env /sudp_app/.venv/

COPY . .

CMD [ "python", "-m", "uvicorn", "main:app", "--reload", "--host", "vacs", "--port", "8000" ]