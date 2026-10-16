import re


def normalize_rut(value: str) -> str:
    compact = re.sub(r"[^0-9kK]", "", str(value)).upper()
    if len(compact) < 2:
        raise ValueError("RUT incompleto")
    body, verifier = compact[:-1], compact[-1]
    if not body.isdigit() or not validate_rut(body + verifier):
        raise ValueError("RUT inválido")
    return f"{int(body)}-{verifier}"


def validate_rut(compact_rut: str) -> bool:
    compact = re.sub(r"[^0-9kK]", "", compact_rut).upper()
    if len(compact) < 2 or not compact[:-1].isdigit():
        return False
    body = compact[:-1]
    expected = compact[-1]
    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - (total % 11)
    verifier = "0" if result == 11 else "K" if result == 10 else str(result)
    return verifier == expected

