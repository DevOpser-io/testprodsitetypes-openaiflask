"""App configuration."""
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
import redis
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_secret(secret_string, region_name):
    secret_name = secret_string
    region_name = region_name
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailure':
            logger.error("Secrets Manager can't decrypt the protected secret text using the provided KMS key")
        elif e.response['Error']['Code'] == 'InternalServiceError':
            logger.error("An error occurred on the server side")
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            logger.error("You provided an invalid value for a parameter")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            logger.error("You provided a parameter value that is not valid for the current state of the resource")
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.error("We can't find the resource that you asked for")
        else:
            logger.error(f"Unknown error: {e}")
        raise e
    secret = get_secret_value_response['SecretString']
    return secret
    # Your code goes here.

class Config:
    """Set Flask configuration vars from .env file."""
    # General Config
    load_dotenv()
    openai_secret_name = os.getenv('OPENAI_SECRET_NAME')
    flask_secret_name = os.getenv('FLASK_SECRET_NAME')
    region_name = os.getenv('REGION')
    print(f"Loaded OpenAI Secret Name: {openai_secret_name}")
    print(f"Loaded Flask Secret Name: {flask_secret_name}")
    print(f"Using AWS Region: {region_name}")
    
    if openai_secret_name:
        OPENAI_API_KEY = get_secret(openai_secret_name, region_name)
        print(f"Retrieved OpenAI API Key: {OPENAI_API_KEY[:5]}...")  # Only print partial key for security
    else:
        OPENAI_API_KEY = None
    if flask_secret_name:
        FLASK_SECRET_KEY = get_secret(flask_secret_name, region_name)
        print(f"Retrieved Flask Secret Key: {FLASK_SECRET_KEY[:5]}...")  # Only print partial key for security
    else:
        FLASK_SECRET_KEY = None
    FLASK_APP = os.getenv('FLASK_APP')
    FLASK_ENV = os.getenv('FLASK_ENV')
    port = int(os.getenv('PORT', 8000))
    host='0.0.0.0'
    debug=True

    # Cache Version Config
    CACHE_VERSION = os.getenv('CACHE_VERSION', f"1.0-{int(time.time())}")
    print(f"Using Cache Version: {CACHE_VERSION}")

    # Session Config
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = f'session:{CACHE_VERSION}:'
    SESSION_REDIS = redis.from_url(os.getenv('REDIS_URL'))

    # Redis client
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_CLIENT = redis.from_url(REDIS_URL)

    print(f"Redis URL: {REDIS_URL}")
    print(f"Session Key Prefix: {SESSION_KEY_PREFIX}")