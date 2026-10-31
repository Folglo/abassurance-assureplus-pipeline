"""Mise en forme des chiffres : espace pour séparer les milliers (1 000), euro, pourcentage."""


def format_number(value, decimals=0):
    """1234567.8 devient « 1 234 568 » (ou « 1 234 567,8 » avec une décimale)."""
    text = f"{value:,.{decimals}f}".replace(",", " ")
    return text.replace(".", ",")


def format_euro(value):
    """12345.6 devient « 12 346 € »."""
    return f"{format_number(value)} €"


def format_percent(value):
    """1.8 devient « 1,8 % »."""
    return f"{format_number(value, 1)} %"
