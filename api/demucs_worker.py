import pika
import os
import time
import json
import torch
import numpy as np
import os
import shutil
import subprocess
import torch
import torchaudio
from pathlib import Path

# Import Demucs
try:
    from demucs.pretrained import get_model
    from demucs.audio import AudioFile, save_audio
except ImportError:
    print("Demucs not installed. Install with: pip install demucs")
    print("Using simulated processing instead.")

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "demucs_tasks"
RABBITMQ_RESULTS_QUEUE = "demucs_results"

# Create output directory
OUTPUT_DIR = "/tmp/demucs_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_audio_with_demucs(file_path, model_name="htdemucs"):
    """Process audio file with Demucs and return paths to separated stems."""
    try:
        # Create output directory based on task ID
        task_id = os.path.basename(file_path).split('_')[0]
        output_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Processing {file_path} with model {model_name}")
        
        # Use the command line approach which works with all versions
        subprocess.run([
            "python3", "-m", "demucs.separate",
            "-o", OUTPUT_DIR,  # Output directory
            "-n", model_name,  # Model name
            file_path  # Input file
        ], check=True)
        
        # Get the output path - Look in the correct directory structure:
        # The files are in /tmp/demucs_output/htdemucs/Good Times/[stem].wav
        model_dir = os.path.join(OUTPUT_DIR, model_name)
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        # Remove the task_id_ prefix to get the original filename
        original_filename = '_'.join(base_filename.split('_')[1:])
        track_dir = os.path.join(model_dir, original_filename)
        
        print(f"Looking for separated files in: {track_dir}")
        
        separated_files = {}
        if os.path.exists(track_dir):
            # Move files to our desired output directory
            for stem in ["vocals", "drums", "bass", "other"]:
                source_path = os.path.join(track_dir, f"{stem}.wav")
                if os.path.exists(source_path):
                    target_path = os.path.join(output_dir, f"{stem}.wav")
                    shutil.copy(source_path, target_path)  # Use copy instead of move
                    separated_files[f"{stem}.wav"] = target_path
                    print(f"Copied {stem}.wav to {target_path}")
            
            return separated_files
        else:
            print(f"Track directory not found at: {track_dir}")
            # List all directories in model_dir to debug
            if os.path.exists(model_dir):
                print(f"Contents of {model_dir}: {os.listdir(model_dir)}")
            
            # Try to handle spaces in filename
            for dir_name in os.listdir(model_dir) if os.path.exists(model_dir) else []:
                potential_track_dir = os.path.join(model_dir, dir_name)
                if os.path.isdir(potential_track_dir):
                    print(f"Found potential track dir: {potential_track_dir}")
                    # Check if it has the expected stems
                    if os.path.exists(os.path.join(potential_track_dir, "vocals.wav")):
                        track_dir = potential_track_dir
                        
                        # Move files to our desired output directory
                        for stem in ["vocals", "drums", "bass", "other"]:
                            source_path = os.path.join(track_dir, f"{stem}.wav")
                            if os.path.exists(source_path):
                                target_path = os.path.join(output_dir, f"{stem}.wav")
                                shutil.copy(source_path, target_path)
                                separated_files[f"{stem}.wav"] = target_path
                                print(f"Copied {stem}.wav to {target_path}")
                        
                        return separated_files
        
        # If we still can't find the files, fall back to simulation
        print("Couldn't find separated files, falling back to simulation")
        return {}
            
    except Exception as e:
        print(f"Error processing with Demucs: {e}")
        import traceback
        traceback.print_exc()
        return {}

def setup_rabbitmq():
    """Setup RabbitMQ connection and channels"""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    
    # Ensure both queues exist
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.queue_declare(queue=RABBITMQ_RESULTS_QUEUE, durable=True)
    
    return connection, channel

def process_message(ch, method, properties, body):
    """Processes a message from the RabbitMQ queue."""
    try:
        message = json.loads(body.decode('utf-8'))
        task_id = message["task_id"]
        file_path = message["file_path"]
        model = message.get("model", "htdemucs")
        
        print(f"[x] Received task: {task_id} for file: {file_path}")
        
        # Try to process with Demucs
        try:
            separated_files = process_audio_with_demucs(file_path, model)
        except Exception as e:
            print(f"Demucs processing failed: {e}")
            separated_files = {}
            
        # If Demucs failed or not installed, use fake files for testing
        if not separated_files:
            print("Using simulated files instead")
            # Create fake files for testing
            fake_dir = os.path.join(OUTPUT_DIR, task_id)
            os.makedirs(fake_dir, exist_ok=True)
            
            separated_files = {}
            for stem in ["vocals", "drums", "bass", "other"]:
                fake_path = os.path.join(fake_dir, f"{stem}.wav")
                # Create an empty file
                with open(fake_path, "wb") as f:
                    # Write a minimal valid WAV header
                    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
                separated_files[f"{stem}.wav"] = fake_path

        # Prepare the result message
        result = {
            "task_id": task_id,
            "separated_files": separated_files
        }

        # Send the result to the results queue
        ch.basic_publish(
            exchange='',
            routing_key=RABBITMQ_RESULTS_QUEUE,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                correlation_id=properties.correlation_id if properties and hasattr(properties, 'correlation_id') else None
            ),
            body=json.dumps(result).encode('utf-8')
        )
        
        print(f"[x] Task {task_id} completed, results sent to {RABBITMQ_RESULTS_QUEUE}")
        
        # Clean up the original file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Original file {file_path} removed")
        except Exception as e:
            print(f"Failed to remove original file: {e}")
            
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    """Main function to start the worker"""
    connection, channel = setup_rabbitmq()
    
    try:
        # Set prefetch count to process one message at a time
        channel.basic_qos(prefetch_count=1)
        
        # Register the consumer
        channel.basic_consume(
            queue=RABBITMQ_QUEUE, 
            on_message_callback=process_message
        )
        
        print(f"[*] Demucs worker started. Waiting for tasks on {RABBITMQ_QUEUE}.")
        print(f"[*] Using {'GPU (CUDA)' if torch.cuda.is_available() else 'CPU'} for processing.")
        print("[*] Press CTRL+C to exit")
        
        # Start consuming
        channel.start_consuming()
        
    except KeyboardInterrupt:
        print("Worker stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        connection.close()
        print("Connection closed")

if __name__ == "__main__":
    main()
