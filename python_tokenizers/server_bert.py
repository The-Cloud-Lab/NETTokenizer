from flask import Flask, request, jsonify
from transformers import BertTokenizer

app = Flask(__name__)

MODEL_NAME = "prajjwal1/bert-tiny"
tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)

@app.route('/tokenize', methods=['POST'])
def tokenize():
    try:
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({"error": "Missing 'texts' field in request"}), 400

        texts = data['texts']

        tokens = tokenizer(
        texts,  
        add_special_tokens=True,  
        padding=True,  
        return_tensors="pt"  
        )
        
        response = {
            "input_ids": tokens["input_ids"].tolist(),
            "attention_mask": tokens["attention_mask"].tolist(),
            "token_type_ids": tokens["token_type_ids"].tolist()
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8010, debug=True)

