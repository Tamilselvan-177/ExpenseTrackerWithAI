import requests
import json

text = """Cafe Delight
Meal for two
Subtotal : 450.00
Tax : 40.50
Total : 490.50"""

GEMINI_API_KEY = "AIzaSyCAqxuuPEctu52QyndRNUo4pLE27_IdmtE"  # ⚠️ Replace with your actual key
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def analyze_receipt(text):
    # Clean and format the text
    text = text.strip()
    if not text:
        return {
            "amount": 0.0,
            "category": "Others",
            "description": "Empty receipt"
        }

    prompt = f"""
    Analyze this receipt text and provide the following information in JSON format:
    1. Total amount (extract the final total amount)
    2. Category (choose from: Shopping, Medical, Food, Rent, Others)
    3. Brief description of what the receipt is for

    Receipt text:
    {text}

    Response format:
    {{
        "amount": float,
        "category": "string",
        "description": "string"
    }}
    """

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        print(f"Processing receipt text:\n{text}\n")
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        print("Response received:", content)
        
        # Clean up the response by removing markdown code blocks
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.endswith('```'):
            content = content[:-3]  # Remove ```
        content = content.strip()
        
        # Parse the cleaned JSON
        try:
            parsed_content = json.loads(content)
            return parsed_content  # Return the parsed dictionary directly
        except json.JSONDecodeError:
            print("Failed to parse JSON:", content)
            return {
                "amount": 0.0,
                "category": "Others",
                "description": "Failed to parse response"
            }
            
    except Exception as e:
        print("An error occurred:", str(e))
        return {
            "amount": 0.0,
            "category": "Others",
            "description": f"Error: {str(e)}"
        }


# Run the function
# analyze_receipt(text)
