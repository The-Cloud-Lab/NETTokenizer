from flask import Flask, request, jsonify
from transformers import AutoTokenizer

app = Flask(__name__)

MODEL_PATH = "sentence-transformers/paraphrase-MiniLM-L6-v2" 
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

@app.route('/tokenize', methods=['POST'])
def tokenize():
    try:
        data = request.get_json()

        if not isinstance(data, dict) or "texts" not in data:
            return jsonify({"error": "Payload must be a JSON object with a 'texts' field"}), 400

        texts = data["texts"]

        if isinstance(texts, list) and all(isinstance(s, str) for s in texts):
            tokens = tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )

        elif isinstance(texts, list) and all(isinstance(pair, list) and len(pair) == 2 for pair in texts):
            sentences1 = [pair[0] for pair in texts]
            sentences2 = [pair[1] for pair in texts]
            tokens = tokenizer(
                sentences1,
                sentences2,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )
        else:
            return jsonify({"error": "Invalid format. Send list of strings or list of [str, str] pairs."}), 400

        response = {
            "input_ids": tokens["input_ids"].tolist(),
            "attention_mask": tokens["attention_mask"].tolist()
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8011, debug=True)