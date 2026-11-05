import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    func
)
from sqlalchemy.orm import relationship
from database import Base

class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    LAWYER = "LAWYER"

class CaseCategory(str, enum.Enum):
    Civil = "Civil"
    Consumer = "Consumer"
    Criminal = "Criminal"

class MilestoneStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")

class Lawyer(Base):
    __tablename__ = "lawyers"

    lawyer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(120), nullable=False)
    bar_council_id = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(SQLEnum(CaseCategory), nullable=False, index=True)
    experience_years = Column(Integer, nullable=False)
    languages = Column(String(150), nullable=False)
    city = Column(String(80), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(120), nullable=False)
    
    # Financial fee schedules - strictly DECIMAL(10,2) to eliminate rounding errors
    consultation_fee = Column(Numeric(10, 2), nullable=False)
    drafting_fee = Column(Numeric(10, 2), nullable=False)
    hearing_fee = Column(Numeric(10, 2), nullable=False)
    full_case_estimate = Column(Numeric(10, 2), nullable=False)
    
    rating = Column(Numeric(3, 2), default=4.50, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="lawyer")

class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    lawyer_id = Column(Integer, ForeignKey("lawyers.lawyer_id"), nullable=False, index=True)
    case_category = Column(SQLEnum(CaseCategory), nullable=False)
    case_summary = Column(Text, nullable=False)
    total_agreed_fee = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="bookings")
    lawyer = relationship("Lawyer", back_populates="bookings")
    milestones = relationship(
        "CaseMilestone",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="CaseMilestone.stage_number"
    )

class CaseMilestone(Base):
    __tablename__ = "case_milestones"

    milestone_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)  # 1, 2, 3, or 4
    stage_name = Column(String(100), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)  # 15.00, 25.00, 30.00, 30.00
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(MilestoneStatus), default=MilestoneStatus.PENDING, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    booking = relationship("Booking", back_populates="milestones")

    @property
    def stage_no(self) -> int:
        return self.stage_number
