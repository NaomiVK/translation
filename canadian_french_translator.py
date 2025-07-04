import json
import os
import requests
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv('.env')

class CanadianFrenchTranslator:
    def __init__(self):
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.cohere_api_key = os.getenv('COHERE_API_KEY')
        
        if not self.openrouter_api_key or not self.cohere_api_key:
            raise ValueError("Missing API keys in .env file")
    
    def translate_with_openrouter(self, text: str, model: str) -> str:
        """Translate text using OpenRouter API"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        # Customize system prompt based on model
        if "mixtral" in model.lower():
            system_content = "You are a professional translator specializing in French Canadian (Quebec French) translation for the Canada Revenue Agency. Translate the following English text to French Canadian, maintaining the formal government tone and terminology used by the CRA. IMPORTANT: Return ONLY the direct translation without any explanations, notes, commentary, or additional text. Be concise and precise. Do not add explanatory phrases or formatting instructions."
        else:
            system_content = "You are a professional translator specializing in French Canadian (Quebec French) translation for the Canada Revenue Agency. Translate the following English text to French Canadian, maintaining the formal government tone and terminology used by the CRA. Preserve all formatting, URLs, and structure. Return only the translated text without any additional commentary."
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": f"Translate this to French Canadian: {text}"
                }
            ],
            "temperature": 0.2,
            "max_tokens": 500
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        translation = result['choices'][0]['message']['content'].strip()
        
        # Clean up Mixtral's verbose output
        if "mixtral" in model.lower():
            # Remove common verbose phrases
            verbose_patterns = [
                "Note: I am an artificial intelligence",
                "Note: This translation",
                "Note: The translation",
                "Note: Je suis un modèle",
                "Voici la traduction",
                "Here's the translation",
                "Translation:",
                "Traduction:",
                "French Canadian translation:",
                "En français canadien:",
                "Note:",
                "Remarque:",
                "(Note:",
                "[Note:",
            ]
            
            lines = translation.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip lines that start with verbose patterns
                if any(line.startswith(pattern) for pattern in verbose_patterns):
                    continue
                # Skip lines that are just explanatory notes
                if any(pattern in line for pattern in verbose_patterns):
                    continue
                if line:  # Only add non-empty lines
                    cleaned_lines.append(line)
            
            if cleaned_lines:
                translation = cleaned_lines[0]  # Take the first clean line as the translation
        
        return translation
    
    def translate_with_cohere(self, text: str) -> str:
        """Translate text using Cohere API v2"""
        url = "https://api.cohere.ai/v2/chat"
        headers = {
            "Authorization": f"Bearer {self.cohere_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "c4ai-aya-expanse-32b",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional translator specializing in French Canadian (Quebec French) translation for the Canada Revenue Agency. Translate the following English text to French Canadian, maintaining the formal government tone and terminology used by the CRA. Preserve all formatting, URLs, and structure. Return only the translated text without any additional commentary."
                },
                {
                    "role": "user",
                    "content": f"Translate this to French Canadian: {text}"
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['message']['content'][0]['text']
    
    def translate_json_content(self, content: Any, translate_func) -> Any:
        """Recursively translate JSON content"""
        if isinstance(content, dict):
            translated = {}
            for key, value in content.items():
                if key in ['text', 'title', 'description', 'note', 'content', 'additional_info'] and isinstance(value, str):
                    translated[key] = translate_func(value)
                elif key == 'items' and isinstance(value, list):
                    translated[key] = [translate_func(item) if isinstance(item, str) else self.translate_json_content(item, translate_func) for item in value]
                else:
                    translated[key] = self.translate_json_content(value, translate_func)
            return translated
        elif isinstance(content, list):
            return [self.translate_json_content(item, translate_func) for item in content]
        else:
            return content
    
    def translate_document(self, input_file: str, model_name: str, translate_func):
        """Translate entire JSON document"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Translate content
        translated_data = self.translate_json_content(data, translate_func)
        
        # Update metadata
        translated_data['metadata']['language'] = 'fr-CA'
        translated_data['metadata']['translation_date'] = datetime.now().isoformat()
        translated_data['metadata']['translation_model'] = model_name
        
        # Generate output filename
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = f"get_ready_{model_name.replace('/', '_').replace('-', '_')}_{date_str}.json"
        
        # Save translated document
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=2)
        
        return output_file

def main():
    translator = CanadianFrenchTranslator()
    input_file = "/home/naomi/Documents/vs-code-projects/translation/get_ready.json"
    
    models = [
        ("openai/gpt-4o-mini", lambda text: translator.translate_with_openrouter(text, "openai/gpt-4o-mini")),
        ("mistralai/mixtral-8x7b-instruct", lambda text: translator.translate_with_openrouter(text, "mistralai/mixtral-8x7b-instruct")),
        ("c4ai-aya-expanse-32b", translator.translate_with_cohere)
    ]
    
    for model_name, translate_func in models:
        try:
            print(f"Translating with {model_name}...")
            output_file = translator.translate_document(input_file, model_name, translate_func)
            print(f"Translation completed: {output_file}")
        except Exception as e:
            print(f"Error translating with {model_name}: {e}")

if __name__ == "__main__":
    main()