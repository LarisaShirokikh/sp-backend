# app/utils/sms.py
def send_sms_verification_code(phone: str, code: str) -> None:
    """
    Отправляет SMS с 6-значным кодом подтверждения.
    Здесь реализуйте вызов API вашего SMS-провайдера.
    """
    # Пример: вывод в консоль, заменить на реальный вызов API
    print(f"Отправка SMS на номер {phone} с кодом: {code}")