from app.core.config import TERMINAL_KEY, PASSWORD
import hashlib


def gen_token(amount, description, order_id) -> str:
    mass = [
        {"TerminalKey": TERMINAL_KEY},
        {"Amount": f"{amount}"},
        {"OrderId": f"{order_id}"},
        {"Description": description},
        {"Password": PASSWORD},
    ]

    sorted_mass = sorted(mass, key=lambda x: list(x.keys())[0])

    concatenated_string = "".join([list(item.values())[0] for item in sorted_mass])
    sha256_hash = hashlib.sha256(concatenated_string.encode("utf-8")).hexdigest()

    return sha256_hash


def gen_token_sbp(payment_id) -> str:
    mass = [
        {"TerminalKey": TERMINAL_KEY},
        {"PaymentId": payment_id},
        {"DataType": "PAYLOAD"},
        {"Password": PASSWORD},
    ]

    sorted_mass = sorted(mass, key=lambda x: list(x.keys())[0])

    concatenated_string = "".join([list(item.values())[0] for item in sorted_mass])
    sha256_hash = hashlib.sha256(concatenated_string.encode("utf-8")).hexdigest()

    return sha256_hash
