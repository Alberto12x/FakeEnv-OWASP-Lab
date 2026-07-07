"""Hash de contraseñas.

A propósito usamos MD5 con un salt global y estático en lugar de un algoritmo
lento y con salt por usuario (bcrypt/Argon2). Es el caso A02 del Top 10: el
hash es rápido de calcular y, al ser el salt común, dos contraseñas iguales
producen el mismo digest, lo que abre la puerta a rainbow tables.
"""

import hashlib

from flask import current_app


def hash_password(password: str) -> str:
    salt = current_app.config["PASSWORD_SALT"]
    return hashlib.md5(f"{salt}{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash
