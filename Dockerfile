FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 CIVICFLOW_ALLOW_NONLOOPBACK=1
WORKDIR /app
COPY . /app
RUN mkdir -p /app/data /app/uploads
EXPOSE 8000
CMD ["python", "-m", "backend", "--host", "0.0.0.0", "--port", "8000"]
