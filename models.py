import enum
import datetime
from database import BaseModel

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Column, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flask_security import UserMixin, RoleMixin


roles_users = Table(
    "roles_users",
    BaseModel.metadata,
    Column("user_id", ForeignKey("user.id")),
    Column("role_id", ForeignKey("role.id")),
)


class Role(BaseModel, RoleMixin):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)


class User(BaseModel, UserMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean(), default=True)
    fs_uniquifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=roles_users, backref="users"
    )


class Employee(BaseModel):
    __tablename__ = "employee"

    id: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    casual_leaves: Mapped[int] = mapped_column(default=0)
    gazzetted_leaves: Mapped[int] = mapped_column(default=0)
    compensatory_leaves: Mapped[int] = mapped_column(default=0)
    without_pay_leaves: Mapped[int] = mapped_column(default=0)
    half_casual_leaves: Mapped[int] = mapped_column(default=0)
    last_reset_year: Mapped[str] = mapped_column(
        String(4), default=lambda: str(__import__("datetime").datetime.now().year)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean(), default=False)

    leaves: Mapped[list["Leave"]] = relationship(
        "Leave", back_populates="employee", cascade="all, delete-orphan"
    )


class LeaveType(enum.Enum):
    CASUAL = "CL"
    GAZZETTED = "GL"
    COMPENSATORY = "COMP"
    WITHOUT_PAY = "WP"
    HALF_CL = "1/2 CL"


class Leave(BaseModel):
    __tablename__ = "leave"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey(Employee.id), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="leaves")
