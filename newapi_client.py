# youtube_analyzer/clients/gemini_client.py
import logging
import os
import json
import requests
from typing import Optional
from retry import retry

# Configure logging with line numbers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


class GeminiClient:
    """A simplified client for interacting with Gemini via NewAPI."""

    def __init__(self, api_key: Optional[str] = None):
        logger.info("Initializing GeminiClient...")

        self.api_key = api_key or os.getenv('NEWAPI_API_KEY', 'sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu')
        if not self.api_key:
            logger.error("No API key provided or found in environment variables")
            raise ValueError("NEWAPI_API_KEY is required to initialize GeminiClient.")

        self.base_url = os.getenv("NEWAPI_BASE_URL", "http://27.152.58.86:51099")
        self.model = "gemini-2.5-flash"

    @retry(exceptions=requests.exceptions.RequestException, tries=3, delay=2, backoff=2, max_delay=10)
    def analyze_text(self, text: str, prompt: str) -> Optional[str]:
        """分析给定文本并返回JSON字符串结果"""
        logger.info("Starting analyze_text request")

        if not text or not prompt:
            logger.warning("Empty text or prompt provided")


        # 构建请求URL和payload
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        full_prompt = f"{prompt}\n\n---\n\n{text}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        # 记录请求信息
        logger.info(f"Request URL: {self.base_url}/v1beta/models/{self.model}:generateContent")
        logger.debug(f"Full URL: {url[:100]}...")  # 只显示前100个字符避免暴露完整API key
        logger.info(f"Request payload size: {len(json.dumps(payload))} bytes")
        logger.debug(f"Prompt length: {len(prompt)}, Text length: {len(text)}")
        logger.debug(f"Full prompt preview: {full_prompt[:200]}...")

        try:
            logger.info("Sending POST request to API...")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # 添加超时设置
            )

            # 记录响应信息
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content length: {len(response.text)} bytes")
            logger.debug(f"Response content preview: {response.text[:500]}...")

            response.raise_for_status()

            result = response.json()
            logger.debug(f"Parsed JSON response: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}...")

            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    response_text = content["parts"][0].get("text", "")
                    logger.info(f"Successfully extracted response text, length: {len(response_text)}")
                    logger.debug(f"Response text preview: {response_text[:200]}...")
                    return response_text

            logger.error("Unexpected response format - missing expected fields")
            logger.error(f"Response structure: {json.dumps(result, indent=2, ensure_ascii=False)}")
            raise ValueError(f"Unexpected API response format: {result}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in analyze_text: {type(e).__name__}: {e}")
            logger.error(f"Full traceback:", exc_info=True)
            raise


def main():
    """主函数"""
    logger.info("Starting main function")
    try:
        logger.info("Creating GeminiClient instance")
        client = GeminiClient()

        logger.info("Calling analyze_text with test data")
        result = client.analyze_text("gemini", "你好")

        if result:
            logger.info("Successfully received result from API")
            print("Result:", result)
        else:
            logger.warning("No result received from API")
            print("Failed to get response")

    except Exception as e:
        logger.error(f"Error in main function: {type(e).__name__}: {e}")
        logger.error("Full traceback:", exc_info=True)
        exit(1)

    logger.info("Main function completed successfully")


if __name__ == '__main__':
    main()