FROM python:3.9
RUN apt-get update && apt-get install -y ffmpeg
RUN mkdir /app && mkdir /auth && mkdir /files
COPY requirements.txt /app
RUN cd /app && pip install -r requirements.txt
COPY . /app

ENTRYPOINT cd /app && python main.py
