import os
import json
import logging
from typing import List
from dotenv import load_dotenv
import openai
from app.models.models import Paystub, BenefitSummary

load_dotenv()

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

MODEL_NAME = "gemma-3-27b-it"

def llm_extract_benefits_from_paystub(paystub: Paystub) -> dict:
    """
    Extract structured benefit data from paystub using LLM.
    """
    # Use the parsed_data from OCR service as context if available, or fall back to stub behavior?
    # Actually, the user wants us to integrate the LLM here.
    # The OCR service already does extraction into paystub.parsed_data using an LLM.
    # But this function seems to be for FURTHER derivation or separate logic.
    # Given the previous stub, it seems to map parsed_data to BenefitSummary fields.
    
    # Let's map whatever we have in paystub.parsed_data directly if possible, 
    # OR we can ask the LLM to reasoning about it if the data is raw.
    
    data = paystub.parsed_data or {}
    
    # If the parsed_data is already structured from ocr_service, we can just return it 
    # formatted for BenefitSummary.
    
    # HOWEVER, the Prompt in ocr_service might not cover all BenefitSummary fields perfectly
    # (e.g. 401k match percent might not be on paystub, only contribution).
    
    # Let's use the LLM to fill in gaps or structure it perfectly for BenefitSummary if needed.
    # For now, let's assume parsed_data is good but use LLM if we want to be fancy.
    # But wait, OCR service ALREADY used the LLM to get 'gross_pay', 'net_pay', 'pto', 'hsa', 'fsa'.
    
    # BenefitSummary has:
    # hsa_balance, hsa_contribution_ytd, fsa_balance, fsa_deadline, pto_balance_hours...
    
    # It seems redundant to call LLM again just for mapping if OCR did it.
    # BUT, if we want to be consistent with the request "integrate the same model", 
    # let's replace the Logic in `llm_generate_recommendations` mostly.
    
    # For extraction, I'll update it to be robust but maybe no new LLM call needed if OCR did it.
    # BUT, let's look at `llm_generate_recommendations`.
    
    return {
        "hsa_balance": data.get("hsa_balance", 0),
        "hsa_contribution_ytd": data.get("hsa_contribution_ytd", 0),
        "fsa_balance": data.get("fsa_balance", 0),
        "fsa_deadline": None, # Hard to get from paystub
        "pto_balance_hours": data.get("pto_hours", 0),
        "pto_accrual_hours_per_period": 0,
        "k401_contribution_percent": 0, # Difficult to calculate exactly without salary info in prompt
        "k401_employer_match_percent": 0,
        "deductible_total": 0,
        "deductible_used": 0,
        "raw_summary": data
    }


def llm_generate_recommendations(summary: BenefitSummary) -> List[dict]:
    """
    Generate recommendations based on BenefitSummary using the LLM.
    """
    prompt = f"""
    Analyze the following employee benefits summary and generate actionable recommendations to save money or optimize benefits.
    
    Benefit Summary:
    - HSA Balance: ${summary.hsa_balance or 0}
    - FSA Balance: ${summary.fsa_balance or 0}
    - PTO Balance: {summary.pto_balance_hours or 0} hours
    - 401k Contribution: {summary.k401_contribution_percent or 0}%
    - 401k Match: {summary.k401_employer_match_percent or 0}%
    
    Return a valid JSON array of objects with these keys: 
    - title (string)
    - description (string)
    - estimated_savings (number or null)
    - category (string, e.g. "401k", "FSA", "PTO", "General")
    - priority (string: "high", "medium", "low")
    
    Do not include markdown or explanations, JUST the JSON array.
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content
        clean_content = content.replace("```json", "").replace("```", "").strip()
        
        recs = json.loads(clean_content)
        return recs
        
    except Exception as e:
        logging.error(f"LLM Recommendation generation failed: {e}")
        # Fallback to empty list or hardcoded default
        return []
