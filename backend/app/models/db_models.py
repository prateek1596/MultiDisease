"""SQLAlchemy ORM models — ENUM names must match PostgreSQL schema exactly."""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    Text, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user  = "user"


class DiseaseType(str, enum.Enum):
    heart    = "heart"
    diabetes = "diabetes"
    kidney   = "kidney"


# ── Explicitly name enums to match the PostgreSQL schema.sql DDL ──────────────
# schema.sql creates:  CREATE TYPE user_role AS ENUM (...)
#                      CREATE TYPE disease_type AS ENUM (...)
# SQLAlchemy by default lowercases the Python class name → "userrole" / "diseasetype"
# which doesn't match → DatatypeMismatchError on INSERT.
# Passing name= + schema= tells asyncpg to use the correct existing type.

_user_role_enum    = SAEnum(UserRole,    name="user_role",    create_type=False)
_disease_type_enum = SAEnum(DiseaseType, name="disease_type", create_type=False)


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50),  unique=True, nullable=False, index=True)
    email           = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(_user_role_enum, default=UserRole.user, nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    predictions = relationship("Prediction", back_populates="user")


class Prediction(Base):
    __tablename__ = "predictions"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True)
    disease_type     = Column(_disease_type_enum, nullable=False)
    model_used       = Column(String(50), nullable=False)
    input_data       = Column(JSON, nullable=False)
    prediction_result= Column(Integer, nullable=False)   # 0 or 1
    prediction_label = Column(String(50), nullable=False)
    confidence       = Column(Float, nullable=False)
    shap_values      = Column(JSON, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="predictions")


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id                   = Column(Integer, primary_key=True, index=True)
    disease_type         = Column(_disease_type_enum, nullable=False)
    model_name           = Column(String(50), nullable=False)
    accuracy             = Column(Float)
    precision            = Column(Float)
    recall               = Column(Float)
    f1_score             = Column(Float)
    roc_auc              = Column(Float)
    confusion_matrix     = Column(JSON)
    classification_report= Column(Text)
    is_best_model        = Column(Boolean, default=False)
    trained_at           = Column(DateTime(timezone=True), server_default=func.now())
