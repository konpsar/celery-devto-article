import os
from dotenv import load_dotenv
from typing import cast
load_dotenv() 

REDIS_HOST: str = cast(str, os.getenv('REDIS_HOST'))
REDIS_PORT: int = int(cast(str, os.getenv('REDIS_PORT')))
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL