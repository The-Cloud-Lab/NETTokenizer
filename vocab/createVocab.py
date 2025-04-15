from transformers import GPT2Tokenizer
import json

# Load GPT-2 tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

# Extract vocabulary
vocab = tokenizer.get_vocab()

# Save to JSON
with open("gpt2_vocab.json", "w") as f:
    json.dump(vocab, f, indent=2)

# Print sample of the vocabulary
print(json.dumps(dict(list(vocab.items())[:10]), indent=2))  # Print first 10 entries

