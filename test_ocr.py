
import os
import fitz  # PyMuPDF
import openai
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional

load_dotenv()

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# Define Pydantic model for structured output
class PaystubData(BaseModel):
    gross_pay: float
    net_pay: float
    pto_hours: Optional[float] = 0.0
    hsa_balance: Optional[float] = 0.0
    fsa_balance: Optional[float] = 0.0

def extract_text_from_pdf(file_path):
    print(f"Extracting text from {file_path}...")
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def test_parsing(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    extracted_text = extract_text_from_pdf(file_path)
    print("-" * 30)
    print("RAW TEXT (First 500 chars):")
    print(extracted_text[:500])
    print("-" * 30)

    if not extracted_text.strip():
        print("No text extracted (Scanned PDF?). Needs OCR.")
        return

    print("Sending to LLM for parsing...")
    
    # Simple prompt - models that support structured output (like gpt-4o-2024-08-06) 
    # handle this via the 'response_format' arg. For others, we assume mostly generic prompting.
    # But since you asked to use Pydantic to ensure format, the best way using standard completion
    # is to ask for the schema in prompt or use tools like Instructor or OpenAI's new beta parsers.
    # Here I will use the standard prompt + Pydantic validation of the response.
    
    prompt = f"""
    Extract the following fields from this paystub text into JSON format:
    - gross_pay (number)
    - net_pay (number)
    - pto_hours (number)
    - hsa_balance (number)
    - fsa_balance (number)
    
    Output must match this JSON schema:
    {json.dumps(PaystubData.model_json_schema(), indent=2)}

    Return ONLY the JSON. No markdown.
    
    Paystub Text:
    {extracted_text[:4000]} 
    """

    try:
        response = client.chat.completions.create(
            model="gemma-3-27b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        print("\nLLM RESPONSE:")
        print(content)
        
        # specific cleanup to handle potential markdown
        clean_content = content.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON and Validate with Pydantic
        try:
             raw_data = json.loads(clean_content)
             validated_data = PaystubData(**raw_data)
             
             print("\n✅ VALIDATED PARSED JSON via PYDANTIC:")
             print(validated_data.model_dump_json(indent=2))
             
        except Exception as validation_error:
             print(f"\n❌ JSON extracted but failed validation: {validation_error}")
             print(f"Extracted JSON: {clean_content}")

    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    FILE_PATH = r"C:\Users\Lenovo\Downloads\Dummy_Payslip_TextBased_v2.pdf"
    
    test_parsing(FILE_PATH)
