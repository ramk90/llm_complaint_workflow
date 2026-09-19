import logging
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import GEMINI_API_KEY, DEFAULT_MODEL
from src.schemas import ComplaintAnalysis, CustomerEmailOutput, ExecutiveSummaryOutput

logger = logging.getLogger(__name__)


def get_genai_client(api_key: Optional[str] = None) -> genai.Client:
    key = api_key or GEMINI_API_KEY
    if key:
        return genai.Client(api_key=key)
    return genai.Client()


@retry(
    retry=retry_if_exception_type(APIError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def generate_content_with_retry(
    client: genai.Client,
    model_name: str,
    contents: str,
    config: types.GenerateContentConfig,
):
    return client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
    )


def extract_complaint_data(
    raw_text: str,
    filename: str,
    model_name: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> ComplaintAnalysis:
    """
    Step 1: Extract structured complaint details, metadata, sentiment, urgency, root cause, and recommendations.
    Uses Gemini API native structured outputs with Pydantic schema validation.
    """
    client = get_genai_client(api_key)

    system_instruction = (
        "You are an expert AI Customer Operations Analyst. "
        "Your task is to analyze raw customer complaint documents, extract key entity details, "
        "categorize the issue, assess urgency and sentiment, hypothesize the root cause, and recommend actionable next steps."
    )

    prompt = f"""
    Please analyze the following raw complaint document (Filename: '{filename}'):

    --- START OF COMPLAINT DOCUMENT ---
    {raw_text}
    --- END OF COMPLAINT DOCUMENT ---

    Extract all relevant details according to the required schema:
    1. Generate or extract a unique Case ID (e.g. CMP-YYYYMMDD-XXX or use filename reference).
    2. Extract customer details (Name, Email, Phone, Account ID, Company Name if mentioned).
    3. Extract incident details (Incident Date, Product/Service Name, Order/Tracking Number, Financial Impact in USD if stated).
    4. Determine the primary Customer Category (BILLING, PRODUCT_QUALITY, DELIVERY_LOGISTICS, SOFTWARE_TECHNICAL, CUSTOMER_SERVICE, OTHER).
    5. Assess Urgency Level (LOW, MEDIUM, HIGH, CRITICAL) and Customer Sentiment (VERY_NEGATIVE, NEGATIVE, NEUTRAL, POSITIVE).
    6. Provide a concise 1-2 sentence Summary.
    7. List specific Key Issues reported.
    8. Formulate a Root Cause Hypothesis.
    9. Recommend internal Action Items and assign the appropriate Department.
    10. Recommend SLA response time in hours (e.g. 2 for CRITICAL, 8 for HIGH, 24 for MEDIUM, 48 for LOW).
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ComplaintAnalysis,
        temperature=0.1,
        system_instruction=system_instruction,
    )

    response = generate_content_with_retry(
        client=client,
        model_name=model_name,
        contents=prompt,
        config=config,
    )

    if not response.parsed:
        raise ValueError(f"Failed to generate structured ComplaintAnalysis output for {filename}")

    return response.parsed  # Returns validated ComplaintAnalysis object directly


def generate_customer_email(
    analysis: ComplaintAnalysis,
    model_name: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> CustomerEmailOutput:
    """
    Step 2: Generate an empathetic, professional customer response email tailored to complaint findings.
    """
    client = get_genai_client(api_key)

    system_instruction = (
        "You are a Senior Customer Relations Manager drafting a personalized response to a customer complaint. "
        "Your message must be empathetic, acknowledge the problem directly, express genuine regret, "
        "reassure the customer with concrete action steps, and maintain high professional standards."
    )

    prompt = f"""
    Based on the structured complaint analysis below, draft a comprehensive customer response email:

    Case ID: {analysis.case_id}
    Customer Name: {analysis.customer.name or 'Valued Customer'}
    Category: {analysis.category.value}
    Urgency: {analysis.urgency.value}
    Summary: {analysis.summary}
    Key Issues: {', '.join(analysis.key_issues)}
    Recommended Action Items: {', '.join(analysis.recommended_action_items)}
    Assigned Department: {analysis.assigned_department}
    Target SLA: {analysis.sla_hours} hours

    Generate:
    1. A subject line referencing Case ID {analysis.case_id}.
    2. A full body email text with salutation, acknowledgement, action plan, next steps, and sign-off.
    3. Communication tone used.
    4. Specific next steps expected from customer (if any).
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CustomerEmailOutput,
        temperature=0.3,
        system_instruction=system_instruction,
    )

    response = generate_content_with_retry(
        client=client,
        model_name=model_name,
        contents=prompt,
        config=config,
    )

    if not response.parsed:
        raise ValueError(f"Failed to generate CustomerEmailOutput for Case ID {analysis.case_id}")

    return response.parsed


def generate_executive_summary(
    analysis: ComplaintAnalysis,
    model_name: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> ExecutiveSummaryOutput:
    """
    Step 3: Generate an internal operations executive summary for management review.
    """
    client = get_genai_client(api_key)

    system_instruction = (
        "You are an Operations Executive & Risk Manager. "
        "Your task is to write a concise internal briefing report for leadership detailing customer impact, "
        "churn risk, financial exposure, root cause, and immediate internal resolution roadmap."
    )

    prompt = f"""
    Create an executive internal briefing summary based on the following case analysis:

    Case ID: {analysis.case_id}
    Customer Name: {analysis.customer.name or 'N/A'} (Company: {analysis.customer.company_name or 'N/A'})
    Category: {analysis.category.value}
    Urgency: {analysis.urgency.value}
    Sentiment: {analysis.sentiment.value}
    Financial Impact: ${analysis.details.financial_impact_usd or 0.0:,.2f}
    Summary: {analysis.summary}
    Root Cause Hypothesis: {analysis.root_cause_hypothesis}
    Assigned Department: {analysis.assigned_department}

    Generate:
    1. An executive headline suitable for daily briefings.
    2. A brief 2-3 sentence operational summary.
    3. Assessment of overall business impact (financial exposure, churn risk, operational bottleneck).
    4. Risk assessment score/rating.
    5. Internal action plan roadmap.
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ExecutiveSummaryOutput,
        temperature=0.2,
        system_instruction=system_instruction,
    )

    response = generate_content_with_retry(
        client=client,
        model_name=model_name,
        contents=prompt,
        config=config,
    )

    if not response.parsed:
        raise ValueError(f"Failed to generate ExecutiveSummaryOutput for Case ID {analysis.case_id}")

    return response.parsed
