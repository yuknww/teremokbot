import time
from datetime import datetime

import psycopg2
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Time,
    ForeignKey,
    BigInteger,
    Text,
    JSON,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from app.core.config import DATABASE_URL, DB_USER, DB_PASSWORD, DB_NAME

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


# ---------- 1. Пользователи (родители) ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    state = Column(String, nullable=True)  # состояние FSM
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    children = relationship(
        "Child", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name={self.full_name})>"


# ---------- 2. Дети ----------
class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    child_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="children")
    registrations = relationship(
        "Registration", back_populates="child", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Child(id={self.id}, name={self.child_name}, user_id={self.user_id})>"


# ---------- 3. Программы ----------
class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)
    age_min = Column(Integer, nullable=False)
    age_max = Column(Integer, nullable=False)

    dates = relationship(
        "DateSlot", back_populates="program", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Program(id={self.id}, name={self.name})>"


# ---------- 4. Даты проведения ----------
class DateSlot(Base):
    __tablename__ = "dates"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    capacity = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    program = relationship("Program", back_populates="dates")
    registrations = relationship(
        "Registration", back_populates="date_slot", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DateSlot(id={self.id}, program_id={self.program_id}, date={self.date}, time={self.time})>"


# ---------- 5. Регистрация ребёнка ----------
class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"))
    date_id = Column(Integer, ForeignKey("dates.id", ondelete="CASCADE"))
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    payment_status = Column(String, default="pending")
    payment_id = Column(String, nullable=True)
    ticket_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    child = relationship("Child", back_populates="registrations")
    date_slot = relationship("DateSlot", back_populates="registrations")
    program = relationship("Program")

    payment = relationship(
        "Payment",
        back_populates="registration",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("child_id", "date_id", name="uq_child_date"),)

    def __repr__(self):
        return f"<Registration(id={self.id}, child_id={self.child_id}, date_id={self.date_id}, status={self.payment_status})>"


# ---------- 6. Платежи ----------
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    registration_id = Column(
        Integer, ForeignKey("registrations.id", ondelete="CASCADE")
    )
    tbank_tx_id = Column(String, nullable=True)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    raw_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    registration = relationship("Registration", back_populates="payment")

    def __repr__(self):
        return f"<Payment(id={self.id}, status={self.status}, amount={self.amount})>"


def wait_for_postgres():
    host = "localhost"
    port = 5432
    print(f"Waiting for Postgres at {host}:{port}...")
    while True:
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
            )
            conn.close()
            print("Postgres is ready!")
            break
        except psycopg2.OperationalError:
            print("Postgres not ready, sleeping 1 second...")
            time.sleep(1)


# ---------- 2. Создаём таблицы ----------
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created (if they did not exist).")
