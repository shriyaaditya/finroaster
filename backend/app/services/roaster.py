import os
import re
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables (.env)
load_dotenv()

# Initialize the Gemini model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# Initialize the Gemini Chat model (using gemini-3.5-flash as default)
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    google_api_key=api_key,
    temperature=0.85
)

class CopilotAction(BaseModel):
    target_vendor: str = Field(description="Target vendor name, e.g. Amazon Prime, Netflix")
    action_mode: Literal["playwright_auto", "tavily_search"] = Field(description="Action mode for cancellation execution")
    requires_auth: bool = Field(description="True if password/login intervention is expected")
    target_url: Optional[str] = Field(default=None, description="Optional URL for deep-link/Tavily steps")
    instructions: Optional[str] = Field(default=None, description="Optional summary of steps if tavily_search is used")

# System Prompt detailing constraints and persona
SYSTEM_PROMPT = """You are the "Financial Roaster" - a sharp, sarcastic, yet legally safe AI assistant.
Your goal is to look at a user's historical spend, a 14-day zero-shot financial forecast, and any flagged parasitic subscription copilot action, then deliver a hilarious 2-sentence roast.

CONSTRAINTS:
1. Sarcastic but NEVER abusive or vulgar.
2. Absolutely DO NOT give investment, trading, or legal advice.
3. GROUNDING: Do not hallucinate or state any financial numbers (amounts, dates, percentiles) that are not present in the provided data. If you refer to numbers, only refer to the exact values in the input data.
4. If a recurring subscription copilot action is provided in the context, seamlessly weave a command into the roast telling the user to kill/cancel it using the provided action data.
5. Output must be exactly 2 sentences long.
"""

USER_PROMPT_TEMPLATE = """Here is the financial data:

HISTORICAL SPEND SUMMARY:
- Categories and average spend: {categories_summary}
- Total spending in history: ${total_historical_spend:.2f}

14-DAY FORECAST SUMMARY (Median p50):
- Forecasted median spend for the next 14 days starts at ${start_forecast:.2f} and ends at ${end_forecast:.2f}.
- Maximum projected daily spending (p90): ${max_projected_spend:.2f}

SUBSCRIPTION COPILOT ACTION CONTEXT:
{subscription_context}

Write a funny, sarcastic 2-sentence roast about my spending behavior and where it is heading. If a subscription copilot action is flagged above, seamlessly tell me to kill that subscription.
"""

def generate_roast(
    historical_transactions: List[Dict[str, Any]], 
    forecast_data: List[Dict[str, Any]],
    copilot_action: Optional[Dict[str, Any]] = None
) -> str:
    # 1. Analyze historical spend
    categories = {}
    total_historical = 0.0
    for tx in historical_transactions:
        amount = tx.get("amount", 0.0)
        category = tx.get("category", "General")
        categories[category] = categories.get(category, 0.0) + amount
        total_historical += amount

    categories_summary = ", ".join([f"{cat} (${val:.2f})" for cat, val in categories.items()])
    
    # 2. Analyze forecast data
    if forecast_data:
        start_forecast = forecast_data[0].get("p50", 0.0)
        end_forecast = forecast_data[-1].get("p50", 0.0)
        max_projected_spend = max([f.get("p90", 0.0) for f in forecast_data])
    else:
        start_forecast = 0.0
        end_forecast = 0.0
        max_projected_spend = 0.0

    # 3. Build Subscription Context string
    if copilot_action and isinstance(copilot_action, dict) and copilot_action.get("target_vendor"):
        vendor = copilot_action.get("target_vendor")
        mode = copilot_action.get("action_mode", "tavily_search")
        url = copilot_action.get("target_url", "")
        subscription_context = f"Flagged parasitic recurring subscription: {vendor}. Action mode: {mode}. Link/Target: {url}."
    else:
        subscription_context = "No parasitic recurring subscriptions detected."

    # 4. Build LangChain Runnable
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT_TEMPLATE)
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    # 5. Generate Roast
    raw_roast = chain.invoke({
        "categories_summary": categories_summary,
        "total_historical_spend": total_historical,
        "start_forecast": start_forecast,
        "end_forecast": end_forecast,
        "max_projected_spend": max_projected_spend,
        "subscription_context": subscription_context
    })
    
    # 6. Clean up response
    clean_roast = raw_roast.strip().replace('"', '').replace('\n', ' ')
    
    # Strict validation: Enforce maximum of 2 sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean_roast)
    if len(sentences) > 2:
        clean_roast = " ".join(sentences[:2])
        
    return clean_roast

if __name__ == "__main__":
    # Quick standalone test
    sample_hist = [
        {"date": "2026-08-01", "amount": 120.0, "category": "Dining"},
        {"date": "2026-08-02", "amount": 450.0, "category": "Shopping"},
        {"date": "2026-08-03", "amount": 35.0, "category": "Transport"}
    ]
    sample_forecast = [
        {"date": "2026-08-04", "p10": 10.0, "p50": 50.0, "p90": 100.0},
        {"date": "2026-08-17", "p10": 20.0, "p50": 80.0, "p90": 250.0}
    ]
    sample_copilot = {
        "target_vendor": "Netflix",
        "action_mode": "playwright_auto",
        "requires_auth": True,
        "target_url": "https://www.netflix.com/youraccount",
        "instructions": None
    }
    print("Testing roast generation with Copilot action...")
    print(generate_roast(sample_hist, sample_forecast, sample_copilot))
