FROM python:3.11-slim
WORKDIR /app
COPY lab2 /app
EXPOSE 8082 8083
ENV PORT=8083
CMD ["python", "server_threaded_locked.py"]
