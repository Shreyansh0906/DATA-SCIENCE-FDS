# Dockerfile

FROM python:3.10-slim

WORKDIR /app
COPY ./src /app

RUN pip install flask requests

ENV FLASK_APP=node.py

CMD ["python", "node.py"]
