FROM python:3.11-slim

WORKDIR /app
COPY . .

EXPOSE 4173
CMD ["python3", "server.py"]
