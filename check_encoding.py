import sys
data = open('storage/users.csv', 'rb').read()
print('First 100 bytes:', data[:100])
print('Length:', len(data))

# Try to decode as UTF-16
try:
    text = data.decode('utf-16')
    print('UTF-16 decode successful')
    print('First line:', text.split('\n')[0])
except Exception as e:
    print('UTF-16 decode failed:', e)

# Try to decode as UTF-16LE
try:
    text = data.decode('utf-16-le')
    print('UTF-16LE decode successful')
    print('First line:', text.split('\n')[0])
except Exception as e:
    print('UTF-16LE decode failed:', e)
