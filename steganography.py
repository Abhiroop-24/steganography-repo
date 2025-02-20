from PIL import Image
import numpy as np
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64

def generate_key(password):
    password = password.encode()  # Convert to bytes
    salt = b'salt_'  # Use a fixed salt for simplicity
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password)
    return key

def encrypt_message(message, key):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_message = encryptor.update(message.encode()) + encryptor.finalize()
    return base64.b64encode(iv + encrypted_message).decode()

def decrypt_message(encrypted_message, key):
    encrypted_message = base64.b64decode(encrypted_message)
    iv = encrypted_message[:16]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(encrypted_message[16:]) + decryptor.finalize()
    return decrypted_message.decode()

def encode_image(image_path, message, output_path, password):
    key = generate_key(password)
    encrypted_message = encrypt_message(message, key)

    image = Image.open(image_path)
    encoded_image = image.copy()
    width, height = image.size
    encrypted_message += '\0'  # Null-terminate the message
    message_bits = ''.join([format(ord(char), '08b') for char in encrypted_message])
    message_bits += '0' * (width * height * 3 - len(message_bits))  # Pad with zeros

    pixels = np.array(image)
    flat_pixels = pixels.flatten()
    for i in range(len(message_bits)):
        flat_pixels[i] = (flat_pixels[i] & ~1) | int(message_bits[i])

    encoded_pixels = flat_pixels.reshape((height, width, 3))
    encoded_image = Image.fromarray(encoded_pixels.astype('uint8'))
    encoded_image.save(output_path)

def decode_image(image_path, password):
    key = generate_key(password)

    image = Image.open(image_path)
    pixels = np.array(image)
    flat_pixels = pixels.flatten()
    message_bits = [str(flat_pixels[i] & 1) for i in range(len(flat_pixels))]
    message_bytes = [int(''.join(message_bits[i:i+8]), 2) for i in range(0, len(message_bits), 8)]
    encrypted_message = ''.join([chr(byte) for byte in message_bytes]).split('\0')[0]

    try:
        decrypted_message = decrypt_message(encrypted_message, key)
        return decrypted_message
    except Exception as e:
        print(f"Decryption error: {e}")  # Debug print
        return None
