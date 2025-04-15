import socket
import threading
from transformers import BertTokenizer
import numpy as np
import json
from flask import Flask, jsonify

# Initialize Flask app (optional, for health check)
app = Flask(__name__)

# Load the BERT tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# UDP server settings
UDP_IP = "0.0.0.0"
UDP_PORT = 8000
BUFFER_SIZE = 65536  # Max UDP payload size

def udp_server():
    """Handle incoming UDP packets."""
    print(f"[UDP] Listening on port {UDP_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        try:
            payload = data.decode('utf-8')
            print(f"[UDP] Received from {addr}: {payload}")

            # Assuming the payload is a single string or a JSON list of strings
            try:
                # Try to parse as JSON array
                texts = json.loads(payload)
                if not isinstance(texts, list):
                    texts = [str(texts)]
            except json.JSONDecodeError:
                texts = [payload]

            # Tokenize
            encoding = tokenizer(
                texts,
                return_tensors='np',
                max_length=128,     # You can modify this as needed
                padding='max_length',
                truncation=True
            )

            input_ids = encoding['input_ids'].tolist()
            attention_mask = encoding['attention_mask'].tolist()

            print(f"[TOKENIZED] input_ids: {input_ids}")
            print(f"[TOKENIZED] attention_mask: {attention_mask}")
        except Exception as e:
            print(f"[ERROR] Failed to process UDP packet: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "UDP tokenizer running"}), 200

if __name__ == '__main__':
    # Run the UDP server in a background thread
    udp_thread = threading.Thread(target=udp_server, daemon=True)
    udp_thread.start()

    # Optionally run Flask for health/status API
    app.run(host='0.0.0.0', port=8010)
