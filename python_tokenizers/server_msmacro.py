from flask import Flask, request, jsonify
from transformers import AutoTokenizer

app = Flask(__name__)


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L4-v2"  
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

REFERENCE = "This is a fixed reference passage used for sentence-pair encoding."

@app.route('/tokenize', methods=['POST'])
def tokenize():
    try:
        data = request.get_json()
        texts = data.get("texts", [])

        if not isinstance(texts, list) or len(texts) == 0:
            return jsonify({"error": "'texts' must be a non-empty list of strings"}), 400

        first_sentences = texts
        second_sentences = [REFERENCE] * len(texts)

        tokens = tokenizer(
            first_sentences,
            second_sentences,
            add_special_tokens=True,
            padding=True,
            truncation=True,
            return_token_type_ids=False,
            return_tensors="pt"
        )

        response = {
            "input_ids": tokens["input_ids"].tolist(),
            "attention_mask": tokens["attention_mask"].tolist()
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8012, debug=True)