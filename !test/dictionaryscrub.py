import json

# Load your dictionary
with open(r'C:\Users\User\Downloads\words.json', 'r') as f:
    words = json.load(f)

# Write as plain text, one word per line
with open(r'C:\Users\User\Downloads\words.txt', 'w') as f:
    for word in words:
        f.write(word + '\n')

print(f"Converted {len(words)} words")
