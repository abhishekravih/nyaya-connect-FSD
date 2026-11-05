from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from models import UserRole, CaseCategory, MilestoneStatus

# ================= USER SCHEMAS =================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    role: UserRole = UserRole.CLIENT
    phone: Optional[str] = Field(None, max_length=20)

class UserRegister(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    user_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# ================= LAWYER SCHEMAS =================
class LawyerBase(BaseModel):
    full_name: str
    bar_council_id: str
    category: CaseCategory
    experience_years: int = Field(..., ge=0)
    languages: str
    city: str
    phone: str
    email: EmailStr
    consultation_fee: Decimal = Field(..., ge=0, decimal_places=2)
    drafting_fee: Decimal = Field(..., ge=0, decimal_places=2)
    hearing_fee: Decimal = Field(..., ge=0, decimal_places=2)
    full_case_estimate: Decimal = Field(..., ge=0, decimal_places=2)
    rating: Decimal = Field(default=Decimal("4.50"), ge=0, le=5, decimal_places=2)

class LawyerResponse(LawyerBase):
    lawyer_id: int

    model_config = ConfigDict(from_attributes=True)

# Alias for backwards compatibility
LawyerOut = LawyerResponse

class LawyerDetailResponse(LawyerResponse):
    category_average_fee: Decimal
    fee_comparison_badge: str  # e.g., '12% Below Category Average', 'At Category Average', '15% Above Category Average'

    model_config = ConfigDict(from_attributes=True)

# Alias for backwards compatibility
LawyerDetailOut = LawyerDetailResponse

class LawyerRecommendRequest(BaseModel):
    recommended_case_category: CaseCategory
    urgency_level: Optional[str] = Field("Medium", pattern="^(Low|Medium|High)$")
    max_budget: Optional[Decimal] = Field(None, ge=0)

# ================= MILESTONE SCHEMAS =================
class MilestoneResponse(BaseModel):
    milestone_id: int
    booking_id: int
    stage_no: int
    stage_name: str
    percentage: Decimal
    amount: Decimal
    status: MilestoneStatus
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Alias for backwards compatibility
CaseMilestoneOut = MilestoneResponse

class MilestoneStatusUpdate(BaseModel):
    status: MilestoneStatus

# ================= BOOKING SCHEMAS =================
class BookingCreate(BaseModel):
    user_id: int
    lawyer_id: int
    case_category: CaseCategory
    case_summary: str = Field(..., min_length=10)

class BookingResponse(BaseModel):
    booking_id: int
    user_id: int
    lawyer_id: int
    case_category: CaseCategory
    case_summary: str
    total_agreed_fee: Decimal
    created_at: Optional[datetime] = None
    milestones: List[MilestoneResponse] = []

    model_config = ConfigDict(from_attributes=True)

# Alias for backwards compatibility
BookingOut = BookingResponse
