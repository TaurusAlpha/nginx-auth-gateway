from flask import Flask, request, Response, abort
import boto3
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get debug setting from environment variable
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# Configure logging based on debug setting
if DEBUG:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.debug("Debug logging enabled")
logger.info("Auth validation service initialized")

# Restrict AWS secret name and region via environment variables
SECRET_NAME = os.environ.get("SECRET_NAME", "X-Secret-Header")
REGION_NAME = os.environ.get("AWS_REGION", "eu-west-1")
logger.info(f"Using secret name: {SECRET_NAME} in region: {REGION_NAME}")

# Limit allowed HTTP methods
ALLOWED_METHODS = {"GET", "HEAD"}

def unescape_json_string(s):
    """
    Properly unescape a JSON string that might contain escaped characters.
    This handles cases where characters like backslashes might be double-escaped.
    """
    if s is None:
        return None
    
    # Handle common JSON escape sequences
    return json.loads(f'"{s}"') if isinstance(s, str) and '\\' in s else s

def get_secret():
    """Retrieve secret from AWS Secrets Manager securely."""
    logger.info("Retrieving secret from AWS Secrets Manager")
    if DEBUG:
        logger.debug(f"Attempting to retrieve secret {SECRET_NAME} from region {REGION_NAME}")
    client = boto3.client("secretsmanager", region_name=REGION_NAME)
    response = client.get_secret_value(SecretId=SECRET_NAME)
    if DEBUG:
        logger.debug("Secret retrieved successfully")
    else:
        logger.info("Secret retrieved successfully")
    
    try:
        secret_string = response["SecretString"]
        secret_data = json.loads(secret_string)
        
        # Unescape all values in the secret_data
        logger.info(f"Processing {len(secret_data)} secret values")
        for key in secret_data:
            secret_data[key] = unescape_json_string(secret_data[key])
            if DEBUG:
                logger.debug(f"Processed secret value for {key}")
                
        return secret_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret JSON: {str(e)}")
        if DEBUG:
            logger.debug(f"Problematic secret string: {secret_string}")
        raise
    except Exception as e:
        logger.error(f"Error processing secret: {str(e)}")
        raise

@app.before_request
def limit_methods():
    """Allow only specific methods to reduce attack surface."""
    if DEBUG:
        logger.debug(f"Request method: {request.method}, path: {request.path}")
    if request.method not in ALLOWED_METHODS:
        logger.warning(f"Method not allowed: {request.method}")
        abort(405)

@app.route("/pong", methods=["GET"])
def pong():
    """Simple health check endpoint."""
    if DEBUG:
        logger.debug("Ping request received")
    return Response("Pong", status=200)

@app.route("/validate", methods=["GET", "HEAD"])
def validate():
    if DEBUG:
        logger.debug(f"Validation request received from {request.remote_addr}")
        logger.debug(f"Headers received: {request.headers}")
    
    try:
        secret_data = get_secret()
        if DEBUG:
            logger.debug(f"Checking {len(secret_data)} header values")
        
        for header, expected_value in secret_data.items():
            actual_value = request.headers.get(header)
            if DEBUG:
                logger.debug(f"Checking header {header}: expected={expected_value}, actual={actual_value}")
            
            if actual_value != expected_value:
                logging.warning(f"Header mismatch: {header}")
                return Response("Forbidden", status=403)
        
        if DEBUG:
            logger.debug("All headers validated successfully")
        return Response("OK", status=200)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        if DEBUG:
            logger.exception("Detailed exception information:")
        return Response("Internal Server Error", status=500)

if __name__ == "__main__":
    if DEBUG:
        logger.debug("Starting application in DEBUG mode")
    else:
        logger.info("Starting application")
    # Bind only to localhost
    app.run(host="127.0.0.1", port=9000, debug=DEBUG)