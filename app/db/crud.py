from datetime import datetime
from typing import Any
from sqlalchemy import func
from telebot.types import Message
from app.bot.middlewares.logger import logger

from app.db.models import Program
from app.db.models import User, Child, Program, DateSlot, Registration, Payment, Session
import uuid

db_local = Session()
# ---------- Пользователи ----------


def check_phone_and_name(db: Session, telegram_id: int) -> dict:
    """Проверяет указано имя и телефон пользователя в таблице"""
    user = get_user_by_telegram_id(db, telegram_id)
    answer = {}
    if user.full_name is None:
        answer["name"] = None
    else:
        answer["name"] = "OK"

    return answer


def get_user_by_telegram_id(db: Session, telegram_id: int) -> User | None:
    """Получить пользователя по Telegram ID"""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(
    db: Session, telegram_id: int, full_name: str = None, phone: str = None
) -> User:
    """Создать пользователя, если его нет"""
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        return user
    user = User(telegram_id=telegram_id, full_name=full_name, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_state(db: Session, telegram_id: int, state: str):
    """Обновить состояние FSM пользователя"""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    user.state = state
    db.commit()
    return user.state


def update_user_name(db: Session, telegram_id: int, name: str):
    """Обновить данные пользователя"""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    user.full_name = name
    db.commit()
    return user.full_name


def update_user_phone(db: Session, telegram_id: int, phone: str):
    """Обновить данные пользователя"""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    user.phone = phone
    db.commit()
    return user.phone


def get_user_state(db: Session, telegram_id: int) -> str | None:
    """Получить текущее состояние пользователя"""
    user = get_user_by_telegram_id(db, telegram_id)
    return user.state if user else None


def check_user_state(message, state):
    db = Session()
    try:
        user = get_user_by_telegram_id(db, message.from_user.id)
        return user and user.state == state
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# ---------- Дети ----------


def add_child(
    db: Session, user_id: int, child_name: str, birth_date: datetime.date
) -> Child:
    """Добавить ребёнка пользователю"""
    child = Child(user_id=user_id, child_name=child_name, birth_date=birth_date)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def get_children_by_user(db: Session, user_id: int) -> list[type[Child]]:
    """Получить всех детей пользователя"""
    return db.query(Child).filter(Child.user_id == user_id).all()


# ---------- Программы и даты ----------


def get_programs(db: Session) -> list[type[Program]]:
    """Получить все программы"""
    return db.query(Program).all()


def get_program_by_id(db: Session, program_id: int) -> Program | None:
    """Получить программу по ID"""
    return db.query(Program).filter(Program.id == program_id).first()


def get_free_dates(db: Session, program_id: int) -> list[type[DateSlot]]:
    """
    Получить свободные даты по программе.
    Возвращает только те, где booked_count < capacity.
    """
    return (
        db.query(DateSlot)
        .filter(
            DateSlot.program_id == program_id, DateSlot.booked_count < DateSlot.capacity
        )
        .order_by(DateSlot.date, DateSlot.time)
        .all()
    )


def increment_booked_count(db: Session, date_id: int):
    """Увеличить счётчик зарегистрированных на дату"""
    date_slot = db.query(DateSlot).filter(DateSlot.id == date_id).first()
    if date_slot:
        date_slot.booked_count += 1
        db.commit()


def decrement_booked_count(db: Session, date_id: int):
    """Уменьшить счётчик зарегистрированных (при отмене)"""
    date_slot = db.query(DateSlot).filter(DateSlot.id == date_id).first()
    if date_slot and date_slot.booked_count > 0:
        date_slot.booked_count -= 1
        db.commit()


# ---------- Регистрация ----------


def register_child(
    db: Session, child_id: int, date_id: int, program_id: int
) -> Registration | None:
    """
    Зарегистрировать ребёнка на выбранную дату и программу.
    Проверяет, есть ли свободные места и нет ли дубликата.
    """
    date_slot = db.query(DateSlot).filter(DateSlot.id == date_id).first()
    if not date_slot:
        raise ValueError("Дата не найдена")

    if date_slot.booked_count >= date_slot.capacity:
        raise ValueError("Мест больше нет")

    existing = (
        db.query(Registration)
        .filter(Registration.child_id == child_id, Registration.date_id == date_id)
        .first()
    )
    if existing:
        raise ValueError("Этот ребёнок уже зарегистрирован на выбранную дату")

    registration = Registration(
        child_id=child_id,
        date_id=date_id,
        program_id=program_id,
        payment_status="pending",
        ticket_code=str(uuid.uuid4()),
    )
    db.add(registration)
    date_slot.booked_count += 1
    db.commit()
    db.refresh(registration)
    return registration


def get_registration_by_ticket(db: Session, ticket_code: str) -> Registration | None:
    """Получить регистрацию по QR-коду (ticket_code)"""
    return (
        db.query(Registration).filter(Registration.ticket_code == ticket_code).first()
    )


def update_registration_payment_status(
    db: Session, registration_id: int, status: str, payment_id: str = None
):
    """Обновить статус оплаты регистрации"""
    registration = (
        db.query(Registration).filter(Registration.id == registration_id).first()
    )
    if not registration:
        raise ValueError("Регистрация не найдена")

    registration.payment_status = status
    if payment_id:
        registration.payment_id = payment_id

    db.commit()
    return registration


def get_user_registrations(db: Session, user_id: int) -> list[type[Registration]]:
    """Получить все регистрации всех детей пользователя"""
    return (
        db.query(Registration)
        .join(Child)
        .filter(Child.user_id == user_id)
        .order_by(Registration.created_at.desc())
        .all()
    )


# ---------- Оплаты ----------


def create_payment(
    db: Session,
    registration_id: int,
    amount: int,
    tbank_tx_id: str = None,
    status: str = "pending",
    raw_response: dict | None = None,
) -> Payment:
    """Создать запись о платеже"""
    payment = Payment(
        registration_id=registration_id,
        tbank_tx_id=tbank_tx_id,
        amount=amount,
        status=status,
        raw_response=raw_response,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(db: Session, tbank_tx_id: str, new_status: str):
    """Обновить статус платежа по TBank transaction id"""
    payment = db.query(Payment).filter(Payment.tbank_tx_id == tbank_tx_id).first()
    if payment:
        payment.status = new_status
        payment.registration.payment_status = (
            "paid" if new_status == "success" else "failed"
        )
        db.commit()
        return payment
    return None


def delete_registration_by_ticket(db: Session, ticket_code: str) -> bool:
    """
    Удаляет регистрацию по ticket_code.
    Возвращает True, если удаление произошло, False если записи не было.
    """
    registration = (
        db.query(Registration).filter(Registration.ticket_code == ticket_code).first()
    )
    if registration:
        db.delete(registration)
        db.commit()
        return True
    return False
