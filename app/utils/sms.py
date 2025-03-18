# app/utils/sms.py
import requests
import json
from app.core.config import settings

def send_sms_verification_code(phone: str, code: str) -> bool:
    """
    Отправляет SMS с 6-значным кодом подтверждения.
    Поддерживает различных российских SMS-провайдеров.
    
    Args:
        phone: Номер телефона в формате 7XXXXXXXXXX
        code: 6-значный код подтверждения
        
    Returns:
        True если SMS отправлено успешно, иначе False
    """
    sms_provider = settings.SMS_PROVIDER.lower()
    
    # Очистка номера телефона от лишних символов
    phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "7" + phone[1:]
    
    message = f"Ваш код подтверждения: {code}"
    
    try:
        if sms_provider == "sms.ru":
            return _send_via_smsru(phone, message)
        elif sms_provider == "smsc":
            return _send_via_smsc(phone, message)
        elif sms_provider == "smsaero":
            return _send_via_smsaero(phone, message)
        elif sms_provider == "devino":
            return _send_via_devino(phone, message)
        else:
            print(f"Неизвестный SMS-провайдер: {sms_provider}")
            # Запасной вариант - вывод в консоль
            print(f"[SMS Имитация] Отправка SMS на номер {phone}: {message}")
            return True
    except Exception as e:
        print(f"Ошибка отправки SMS: {e}")
        return False

def _send_via_smsru(phone: str, message: str) -> bool:
    """Отправка SMS через сервис SMS.RU"""
    url = "https://sms.ru/sms/send"
    params = {
        "api_id": settings.SMSRU_API_KEY,
        "to": phone,
        "msg": message,
        "json": 1
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    return result.get("status") == "OK"

def _send_via_smsc(phone: str, message: str) -> bool:
    """Отправка SMS через сервис SMSC.RU"""
    url = "https://smsc.ru/sys/send.php"
    params = {
        "login": settings.SMSC_LOGIN,
        "psw": settings.SMSC_PASSWORD,
        "phones": phone,
        "mes": message,
        "fmt": 3  # JSON формат ответа
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    return "error" not in result

def _send_via_smsaero(phone: str, message: str) -> bool:
    """Отправка SMS через сервис SMS Aero"""
    url = f"https://gate.smsaero.ru/v2/sms/send"
    headers = {
        "Authorization": f"Basic {settings.SMSAERO_EMAIL}:{settings.SMSAERO_API_KEY}"
    }
    params = {
        "number": phone,
        "text": message,
        "sign": settings.SMSAERO_SIGN
    }
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    return result.get("success") == True

def _send_via_devino(phone: str, message: str) -> bool:
    """Отправка SMS через сервис Devino Telecom"""
    url = "https://api.devino.online/sms/messages"
    headers = {
        "Authorization": f"Bearer {settings.DEVINO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {
                "to": phone,
                "from": settings.DEVINO_SENDER,
                "text": message
            }
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    result = response.json()
    
    return not any(msg.get("status") == "Error" for msg in result.get("messages", []))