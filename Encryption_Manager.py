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


if __name__ == "__main__":

    print("------")

    print(read_private_key("TNV"))

    m = 'UnxQAZZMSxmfmHLQrInhIRtTI6h57guEv7+rPJJRWt/inBsp0/frbK0zeDJqcL30XqGeRcauVJ8+uFuRhYJ1K2w0hl4e90ZFtdg6Ts8KmWXbTqoDrrCgf93MkSHFn1WHMBQ5S51dSgMYTgIG0gNeD0/1rUGUkpwXbjPXtxdVKGyZoIMSXvsLXbZ7IlQAtFWnsLkGh+oP3jNxhEQ0oSzjp3YDOx292rxh/pmZkgUu2lovqgS+fGANTukAtnslLH4bOEV5MfSbRmvEXVgL7sir+h6Fvef5m9C5lB3xrVgGuH8VszOXgp3ZWlbdf58wCWm6Bl9e1lp+dDO0EcdIoUyPdw=='

    t = "b'UnxQAZZMSxmfmHLQrInhIRtTI6h57guEv7+rPJJRWt/inBsp0/frbK0zeDJqcL30XqGeRcauVJ8+uFuRhYJ1K2w0hl4e90ZFtdg6Ts8KmWXbTqoDrrCgf93MkSHFn1WHMBQ5S51dSgMYTgIG0gNeD0/1rUGUkpwXbjPXtxdVKGyZoIMSXvsLXbZ7IlQAtFWnsLkGh+oP3jNxhEQ0oSzjp3YDOx292rxh/pmZkgUu2lovqgS+fGANTukAtnslLH4bOEV5MfSbRmvEXVgL7sir+h6Fvef5m9C5lB3xrVgGuH8VszOXgp3ZWlbdf58wCWm6Bl9e1lp+dDO0EcdIoUyPdw=='"
    print(str(t))
    print(t[2:len(t)-1])
    print(decrypt_with_private_key(read_private_key("TNV"),m))


