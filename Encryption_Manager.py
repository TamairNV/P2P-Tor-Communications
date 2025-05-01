import base64
import os

from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding, padding
from cryptography.hazmat.primitives import hashes

import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


def keys_to_strings(private_key, public_key):
    # Private key as string
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Public key as string
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem


def encrypt_with_public_key_pem(public_key_pem: str, message: str) -> str:
    """
    Encrypt a message using a public key in PEM format.
    Returns: Base64-encoded ciphertext (for easy storage/transmission).
    """
    # 1. Load the public key from PEM string
    public_key = serialization.load_pem_public_key(
        public_key_pem,
        backend=default_backend()
    )

    # 2. Encrypt using RSA-OAEP (recommended for security)
    ciphertext = public_key.encrypt(
        message.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # 3. Return as base64 string (safe for storage/JSON)
    return base64.b64encode(ciphertext).decode("utf-8")

def read_private_key(username):
    with open("Data/Keys/" + username + "/" + "priv_key.pem","r") as f:
        private_key = serialization.load_pem_private_key(f.read().encode(), backend=default_backend(),password=None)
    return private_key


# Example Usage

def decrypt_with_private_key(private_key, ciphertext):
    ciphertext = base64.b64decode(ciphertext)
    plaintext = private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode()


def init_password(plaintext):
    salt = os.urandom(16)
    hashed_password = hashlib.sha256(salt + plaintext.encode()).digest()

    return hashed_password, salt


def check_password(hashed_password, salt, plaintext):
    hashed_password_new = hashlib.sha256(salt + plaintext.encode()).digest()
    return hashed_password_new == hashed_password


def load_private_key_from_string(private_pem_str, password=None):
    private_key = serialization.load_pem_private_key(
        private_pem_str.encode('utf-8'),
        password=password.encode() if password else None,
        backend=default_backend()
    )
    return private_key



import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend


def create_symmetric_key() -> str:
    """
    Creates a symmetric key and returns it as a base64-encoded string.
    """
    key = os.urandom(32)  # AES-256 requires a 32-byte key
    return base64.b64encode(key).decode('utf-8')


def encrypt_message_with_symmetric_key(symmetric_key: str, message: str) -> str:
    """
    Encrypts a message using the symmetric key.

    :param symmetric_key: The symmetric key as a base64-encoded string.
    :param message: The plaintext message to encrypt.
    :return: The encrypted message as a base64-encoded string.
    """
    key = base64.b64decode(symmetric_key.encode('utf-8'))
    iv = os.urandom(16)  # Generate a random initialization vector (IV)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

    padder = PKCS7(algorithms.AES.block_size).padder()
    padded_message = padder.update(message.encode('utf-8')) + padder.finalize()

    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_message) + encryptor.finalize()

    # Return the IV and ciphertext concatenated and base64-encoded
    return base64.b64encode(iv + ciphertext).decode('utf-8')


def decrypt_message_with_symmetric_key(symmetric_key: str, encrypted_message: str) -> str:
    """
    Decrypts a message using the symmetric key.

    :param symmetric_key: The symmetric key as a base64-encoded string.
    :param encrypted_message: The encrypted message as a base64-encoded string.
    :return: The decrypted plaintext message as a string.
    """
    key = base64.b64decode(symmetric_key.encode('utf-8'))
    encrypted_data = base64.b64decode(encrypted_message.encode('utf-8'))

    iv = encrypted_data[:16]  # Extract the IV
    ciphertext = encrypted_data[16:]  # Extract the ciphertext

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_message = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = PKCS7(algorithms.AES.block_size).unpadder()
    message = unpadder.update(padded_message) + unpadder.finalize()

    return message.decode('utf-8')



if __name__ == "__main__":

    syKey = create_symmetric_key()
    print(syKey)
    message = "Hello World!"

    encrypted_message = encrypt_message_with_symmetric_key(syKey, message)

    print(encrypted_message)

    decrypted_message = decrypt_message_with_symmetric_key(syKey, encrypted_message)
    print(decrypted_message)

