import hashlib

from cryptography.hazmat.decrepit.ciphers import algorithms

from cryptography.hazmat.primitives import serialization, padding, hmac
import os

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import hmac
import hashlib

def generate_key_pair():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize keys for storage
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return priv_bytes, pub_bytes


def encrypt_message(key, message):
    # AES-256-CBC with HMAC-SHA256
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    # Pad the message
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Add HMAC
    hmac_key = hashlib.sha256(key).digest()
    mac = hmac.new(hmac_key, iv + ciphertext, hashlib.sha256).digest()

    return iv + ciphertext + mac


def decrypt_message(key, encrypted):
    iv = encrypted[:16]
    ciphertext = encrypted[16:-32]
    received_mac = encrypted[-32:]

    # Verify HMAC
    hmac_key = hashlib.sha256(key).digest()
    mac = hmac.new(hmac_key, iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, received_mac):
        raise ValueError("Invalid MAC")

    # Decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext