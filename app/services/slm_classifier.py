import random

class SLMClassifier:
    """
    Simulates a Fine-Tuned Small Language Model (SLM) for text classification.
    In production, this would load an ONNX model or call a local inference server (e.g., Llama.cpp).
    """
    
    MODEL_NAME = "ClearPerks-Phi3-Mini-4k-Instruct-Quantized"
    
    @staticmethod
    def classify_text(text: str) -> dict:
        """
        Classifies the input text into established Benefit categories and priority.
        
        Args:
            text (str): The text to classify (e.g., notification body, trend summary).
            
        Returns:
            dict: {
                "category": str,
                "priority": str,
                "confidence": float,
                "model": str
            }
        """
        # Mock logic to simulate "intelligence" by keyword matching
        text_lower = text.lower()
        
        category = "news" # Default
        priority = "medium"
        confidence = 0.85 + (random.random() * 0.14) # 0.85 - 0.99
        
        # Priority Logic
        if any(w in text_lower for w in ["deadline", "expire", "urgent", "action required", "critical"]):
            priority = "high"
        
        # Category Logic
        if any(w in text_lower for w in ["hsa", "fsa", "401k", "savings", "tax", "finance", "money"]):
            category = "financial" # In models, we mapped this to 'news' or specialized. Let's map to existing categories.
            # NotificationService checks: 'news', 'social', 'gov'. 
            # If we want detailed categories, we need to update NotificationService logic or map back to these.
            # Let's assume 'news' covers general updates, 'gov' implies regulation.
            if "tax" in text_lower or "regulation" in text_lower or "irs" in text_lower:
                category = "gov"
        elif any(w in text_lower for w in ["pto", "vacation", "leave", "holiday"]):
            category = "news" 
        elif any(w in text_lower for w in ["health", "medical", "dental", "vision"]):
            category = "news"
        elif any(w in text_lower for w in ["community", "event", "social", "party"]):
            category = "social"
            
        return {
            "category": category,
            "priority": priority,
            "confidence": round(confidence, 4),
            "model": SLMClassifier.MODEL_NAME
        }
