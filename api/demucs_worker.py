import pika
import os
import time
import json

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "demucs_tasks"

connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

def process_message(ch, method, properties, body):
    """
    Processes a message from the RabbitMQ queue.
    """
    try:
        # Replace eval() with json.loads()
        message = json.loads(body.decode('utf-8'))  # Decode to string, then parse JSON
        task_id = message["task_id"]
        print(f" [x] Received task: {task_id} (Placeholder processing)")
        properties.reply_to = "demucs_results"  # Set the reply queue

        # Simulate processing (wait a few seconds)
        time.sleep(2)

        # Simulate results (always the same)
        separated_files = {
            "vocals.wav": "/tmp/fake_vocals.wav",
            "drums.wav": "/tmp/fake_drums.wav",
            "bass.wav": "/tmp/fake_bass.wav",
            "other.wav": "/tmp/fake_other.wav",
        }

        result = {"status": "completed", "separated_files": separated_files}

        print(f" [x] Task {task_id} completed (Placeholder)")

        # Reply to the queue from the header, if reply_to is set
        if properties.reply_to:
            # Encode the result to JSON before sending
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(correlation_id=properties.correlation_id),
                body=json.dumps(result).encode('utf-8')  # JSON-encode the response
            )
        else:
            print(" [!] No reply_to property found in message.")

        ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge message

    except Exception as e:
        print(f"Error processing message: {e}")

channel.basic_qos(prefetch_count=1)  # Only one message at a time per worker
channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_message)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
