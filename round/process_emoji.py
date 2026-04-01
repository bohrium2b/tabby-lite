with open("emojis.txt", "r", encoding="utf-8") as f:
    lines = [line.split(';', 1)[0].strip().split() for line in f.readlines() if line.strip() and not line.startswith('#')]

# Keep only the first code point of each emoji
emojis = [line[0] for line in lines]
with open("emoji_unicode.txt", "w", encoding="utf-8") as f:
    for emoji in set(emojis):
        f.write(f"{chr(int(emoji, 16))}\n")