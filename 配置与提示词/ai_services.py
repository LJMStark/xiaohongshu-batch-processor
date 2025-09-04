import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- OpenRouter/DeepSeek API Client ---
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# --- SiliconFlow API Configuration ---
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")

# --- Moonshot API Client ---
moonshot_client = OpenAI(
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url="https://api.moonshot.cn/v1",
)

def rewrite_content(text, prompt_template):
    """
    Rewrites the given text using the primary AI model (OpenRouter) with a fallback
    to a secondary model (DeepSeek).
    
    Args:
        text: The original text to rewrite
        prompt_template: The prompt template for rewriting
        
    Returns:
        str: The rewritten content
        
    Raises:
        Exception: If both primary and backup models fail
    """
    # Try OpenRouter first
    try:
        completion = openrouter_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/xiaohongshu-batch-processor",
                "X-Title": "Xiaohongshu Batch Processor",
            },
            model="deepseek/deepseek-r1-0528:free",
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"OpenRouter API failed: {e}")
        print("Trying DeepSeek backup model...")
        
        # Fallback to DeepSeek via SiliconFlow
        try:
            payload = {
                "model": "deepseek-ai/DeepSeek-V3.1",
                "messages": [
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": text}
                ]
            }
            headers = {
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(SILICONFLOW_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e2:
            print(f"DeepSeek backup also failed: {e2}")
            print("Trying Moonshot as final fallback...")
            
            # Final fallback to Moonshot for content rewriting
            try:
                completion = moonshot_client.chat.completions.create(
                    model="kimi-k2-0711-preview",
                    messages=[
                        {"role": "system", "content": prompt_template},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.8,
                )
                return completion.choices[0].message.content
            except Exception as e3:
                raise Exception(f"All models failed. OpenRouter: {e}, DeepSeek: {e2}, Moonshot: {e3}")

def generate_title(text, prompt_template):
    """
    Generates a title for the given text using the Kimi model.
    
    Args:
        text: The content to generate title for
        prompt_template: The prompt template for title generation
        
    Returns:
        str: The generated title
        
    Raises:
        Exception: If the Kimi model fails
    """
    try:
        completion = moonshot_client.chat.completions.create(
            model="kimi-k2-0711-preview",
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": text}
            ],
            temperature=0.6,
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Kimi title generation failed: {e}")
