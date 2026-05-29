FROM python:3.12-slim
WORKDIR /app
# Pure stdlib — no pip installs needed
EXPOSE 5757
# -u = unbuffered stdout so logs appear immediately in docker logs
CMD ["python", "-u", "server.py"]
