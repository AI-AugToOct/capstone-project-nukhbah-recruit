from openai import OpenAI
from src.config import GPT_API_KEY
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


gpt = OpenAI(api_key=GPT_API_KEY)
def get_gpt_client():
    logger.info("Establishing connection with OpenAI...")  
    try:
        logger.info(f"OpenAI Connection Successful!")
        return gpt

    except Exception as e:
        logger.error(f"OpenAI Connection Failed: {e}")
        return None 
