import os
import json
from openai import OpenAI
from typing import Optional, Dict

class AINotificationService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        if not self.api_key:
            # For boilerplate purposes, we don't crash init, but methods will fail or mock.
            print("Warning: OPENAI_API_KEY not found.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_notification_content(self, context: str) -> Dict[str, str]:
        """
        Generates a Title and Body based on the provided context (e.g. event details).
        """
        if not self.client:
            return {"title": "Mock Title", "body": "Mock Body (No API Key)"}

        prompt = f"""
        You are a helpful assistant for a benefits platform. 
        Analyze the following news items and generate a SINGLE notification 'title' and 'body' that summarizes the key updates for this category.
        Do NOT return a list. Return ONLY one JSON object.

        News Items:
        "{context}"
        
        Return the result as valid JSON with keys: "title", "body".
        """

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            
            # Handle potential markdown fencing
            content = content.replace("```json", "").replace("```", "").strip()
            
            # Extract only the first JSON object if extra text exists
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            return json.loads(content)
        except Exception as e:
            print(f"AI Generation Error: {e} | Content: {content if 'content' in locals() else 'None'}")
            return {"title": "Error generating title", "body": "Error generating body"}

    def classify_notification(self, title: str, body: str) -> Dict[str, str]:
        """
        Classifies a notification into a Category and Priority.
        Categories: news, social, gov, manual
        Priorities: high, medium, low
        """
        if not self.client:
            return {"category": "manual", "priority": "medium"}

        prompt = f"""
        Classify the following notification into one of the categories: [news, social, gov, manual]
        and one of the priorities: [high, medium, low].

        Notification Title: "{title}"
        Notification Body: "{body}"

        Return valid JSON with keys: "category", "priority".
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"AI Classification Error: {e}")
            return {"category": "manual", "priority": "medium"}
