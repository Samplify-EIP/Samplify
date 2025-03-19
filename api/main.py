from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import Dict
import pika
import uuid
import os
import shutil
from fastapi.responses import FileResponse
import threading
import json

app = FastAPI()

# RabbitMQ connection parameters (only store configuration, not the connection itself)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "demucs_tasks"
RABBITMQ_RESULTS_QUEUE = "demucs_results"

#Dictionnary to store the results.
task_results: Dict[str, Dict[str, str]] = {}

def create_rabbitmq_connection():
    """Creates a new RabbitMQ connection and channel."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.queue_declare(queue=RABBITMQ_RESULTS_QUEUE, durable=True)
    return connection, channel


def consume_results():
    """Consumes results from the RabbitMQ results queue."""
    connection, channel = create_rabbitmq_connection()  # Create a new connection
    try:
        def callback(ch, method, properties, body):
            try:
                print(f" [x] Received result: {body}")
                message = json.loads(body.decode()) # Use json.loads for safety
                separated_files = message["separated_files"] #Dictionary of filename:path.

                print(f"[*] result : {separated_files}")

                ch.basic_ack(delivery_tag=method.delivery_tag)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=RABBITMQ_RESULTS_QUEUE, on_message_callback=callback)
        channel.start_consuming()

    except Exception as e:
        print(f"Error in consume_results thread: {e}")
    finally:
        connection.close()

@app.on_event("startup")
async def startup_event():
    # Start consuming results in a background thread
    thread = threading.Thread(target=consume_results, daemon=True)
    thread.start()


@app.post("/api/demucs/separate")
async def separate_audio(audio_file: UploadFile = File(...), model: str = "htdemucs"):
    task_id = str(uuid.uuid4())
    file_path = f"/tmp/{task_id}_{audio_file.filename}"
    try:
        with open(file_path, "wb") as f:
            f.write(await audio_file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # Create a new connection for publishing
    connection, channel = create_rabbitmq_connection()
    try:
        message = {
            "task_id": task_id,
            "file_path": file_path,
            "model": model,
        }

        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message).encode(), #Use json.dumps
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )

        print(f" [x] Sent task: {task_id} to RabbitMQ")
        return {"task_id": task_id, "status": "processing"}
    finally:
        connection.close() #Close the connection.

@app.get("/api/demucs/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id in task_results:
        return {"task_id": task_id, "status": "completed", "separated_files": task_results[task_id]}
    else:
        return {"task_id": task_id, "status": "processing"}

@app.get("/api/demucs/results/{task_id}/{filename}")
async def get_demucs_result(task_id: str, filename: str, background_tasks: BackgroundTasks):
    if task_id in task_results and filename in task_results[task_id]:
        file_path = task_results[task_id][filename]
        def cleanup(path: str):
            try:
                os.remove(path)
                del task_results[task_id][filename] #Remove the file once sent
                if not task_results[task_id]:
                    del task_results[task_id]
                print(f"Successfully cleaned up {path}")

            except Exception as e:
                print(f"Failed to clean up {path}: {e}")
        background_tasks.add_task(cleanup, file_path)
        return FileResponse(path=file_path, filename=filename, media_type="audio/wav")
    else:
        raise HTTPException(status_code=404, detail="File not found")
