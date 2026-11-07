"""Authentification de démonstration : deux profils, mots de passe stockés en empreinte bcrypt."""

import bcrypt

# bcrypt refuse les mots de passe de plus de 72 octets.
MAX_PASSWORD_BYTES = 72

USERS = {
    "admin": {
        "role": "admin",
        "password_hash": "$2b$12$QvOGkER.bCdLgBkz7P6mvOxkD29w5zYQV7MkInwzhunx91QWOQil6",
    },
    "user": {
        "role": "user",
        "password_hash": "$2b$12$PQLKlKRn1EiwTN3p3YPcj.MGIiVEBNlUU48Dkkjne36B7VSNkYu1q",
    },
}


def hash_password(password):
    """Empreinte bcrypt du mot de passe, avec un sel aléatoire propre à chaque empreinte."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def authenticate(username, password, users=None):
    """Retourne le rôle (« admin » ou « user ») si les identifiants sont corrects, sinon None."""
    users = USERS if users is None else users
    account = users.get(username)
    if account is None:
        return None
    encoded = password.encode()
    if len(encoded) > MAX_PASSWORD_BYTES:
        return None
    if bcrypt.checkpw(encoded, account["password_hash"].encode()):
        return account["role"]
    return None
