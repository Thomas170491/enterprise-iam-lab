from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db

if TYPE_CHECKING:
    from models.resource import DepartmentResource


class Department(db.Model):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    client_role: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    resources: Mapped[list[DepartmentResource]] = relationship(
        "DepartmentResource",
        back_populates="department",
        cascade="all, delete-orphan",
    )