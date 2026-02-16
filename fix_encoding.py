# Script to convert users.csv from UTF-16 to UTF-8

# Read the UTF-16 encoded file
with open('storage/users.csv', 'r', encoding='utf-16') as f:
    content = f.read()

# Write as UTF-8
with open('storage/users.csv', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully converted users.csv from UTF-16 to UTF-8")

# Verify the conversion
with open('storage/users.csv', 'rb') as f:
    first_bytes = f.read(100)
    print('First 100 bytes after conversion:', first_bytes)
