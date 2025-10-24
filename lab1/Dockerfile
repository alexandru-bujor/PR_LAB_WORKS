FROM python:3.11-slim
WORKDIR /app
COPY server.py /app/server.py
COPY content /app/content
EXPOSE 8080
CMD ["python", "server.py"]
