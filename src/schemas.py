from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Sentiment(str, Enum):
    VERY_NEGATIVE = "VERY_NEGATIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"


class CustomerCategory(str, Enum):
    BILLING = "BILLING"
    PRODUCT_QUALITY = "PRODUCT_QUALITY"
    DELIVERY_LOGISTICS = "DELIVERY_LOGISTICS"
    SOFTWARE_TECHNICAL = "SOFTWARE_TECHNICAL"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    OTHER = "OTHER"


class CustomerInfo(BaseModel):
    name: Optional[str] = Field(default=None, description="Full name of the customer filing the complaint")
    email: Optional[str] = Field(default=None, description="Customer email address if available")
    phone: Optional[str] = Field(default=None, description="Customer contact phone number if available")
    account_id: Optional[str] = Field(default=None, description="Account ID, User ID, or Customer ID")
    company_name: Optional[str] = Field(default=None, description="Organization or company name if business client")


class ComplaintDetails(BaseModel):
    incident_date: Optional[str] = Field(default=None, description="Date when incident occurred (YYYY-MM-DD or text)")
    product_service_name: Optional[str] = Field(default=None, description="Name of product, service, or feature involved")
    order_number: Optional[str] = Field(default=None, description="Order, invoice, or ticket tracking number")
    financial_impact_usd: Optional[float] = Field(default=None, description="Estimated monetary impact in USD")


class ComplaintAnalysis(BaseModel):
    case_id: str = Field(description="Unique case identifier, e.g., CMP-2026-001")
    customer: CustomerInfo = Field(description="Customer information extracted from document")
    details: ComplaintDetails = Field(description="Specific complaint details")
    category: CustomerCategory = Field(description="Primary category of the complaint")
    urgency: UrgencyLevel = Field(description="Assessed urgency/priority level")
    sentiment: Sentiment = Field(description="Customer sentiment")
    summary: str = Field(description="Concise 1-2 sentence overview of the issue")
    key_issues: List[str] = Field(description="List of specific core issues reported")
    root_cause_hypothesis: str = Field(description="Hypothesized root cause")
    recommended_action_items: List[str] = Field(description="Immediate internal action items required")
    assigned_department: str = Field(description="Department responsible for handling this case")
    sla_hours: int = Field(description="Target SLA response window in hours")


class CustomerEmailOutput(BaseModel):
    email_subject: str = Field(description="Professional email subject line including case ID")
    email_body: str = Field(description="Full text of customer response email")
    tone: str = Field(description="Communication tone, e.g., Empathetic, Professional, Urgent")
    next_steps_for_customer: List[str] = Field(description="Action steps or details requested from customer")


class ExecutiveSummaryOutput(BaseModel):
    executive_headline: str = Field(description="One-line executive headline")
    brief_summary: str = Field(description="Internal summary for ops/management")
    business_impact: str = Field(description="Evaluation of financial or operational risk")
    risk_assessment: str = Field(description="Risk level evaluation (e.g. High Risk, Churn Risk)")
    action_plan: List[str] = Field(description="Internal step-by-step resolution roadmap")


class WorkflowResult(BaseModel):
    filename: str
    file_path: str
    status: str  # "SUCCESS" or "FAILED"
    analysis: Optional[ComplaintAnalysis] = None
    email: Optional[CustomerEmailOutput] = None
    summary: Optional[ExecutiveSummaryOutput] = None
    error_message: Optional[str] = None
    processing_time_sec: float = 0.0
