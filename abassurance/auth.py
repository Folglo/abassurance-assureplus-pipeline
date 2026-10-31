"""Authentification de démonstration : deux profils, mots de passe stockés en empreinte."""

import hashlib
import hmac

SALT = "abassurance-demo"

USERS = {
    "admin": {
        "role": "admin",
        "password_hash": "5ccaaaba040278e2f83d7b4c0473d9fef84019d2d4d8d6277cd026891bce0b11",
    },
    "user": {
        "role": "user",
        "password_hash": "a5a6560892835b096d66f916f0b09d62e7edfcdf128d742d58f6fee3f0a05ed3",
    },
}


def hash_password(password):
    """Empreinte SHA-256 salée du mot de passe."""
    return hashlib.sha256(f"{SALT}:{password}".encode()).hexdigest()


def authenticate(username, password, users=None):
    """Retourne le rôle (« admin » ou « user ») si les identifiants sont corrects, sinon None."""
    users = USERS if users is None else users
    account = users.get(username)
    if account is None:
        return None
    if hmac.compare_digest(hash_password(password), account["password_hash"]):
        return account["role"]
    return None
