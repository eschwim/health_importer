FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY libs/ libs/

VOLUME /cache
ENV TOKEN_FILE=/cache/tokens

EXPOSE 8080

CMD ["python3", "main.py"]
