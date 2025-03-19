FROM fastapi-base:latest

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p processed_files && chmod 777 processed_files

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
