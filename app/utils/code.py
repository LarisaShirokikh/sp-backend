# app/utils/code.py
import secrets

def generate_verification_code() -> str:
    """Генерирует случайный 6-значный код в виде строки."""
    return f"{secrets.randbelow(10**6):06d}"