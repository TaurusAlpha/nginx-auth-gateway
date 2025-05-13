import json
import os
import logging
import boto3
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")
SECRET_NAME = os.environ.get("SECRET_NAME", "X-Secret-Header")
REGION_NAME = os.environ.get("AWS_REGION", "eu-west-1")
PORT = 9000

# Configure logging
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
handler.flush = lambda: sys.stdout.flush()  # Force immediate flush

logger = logging.getLogger("validator")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.addHandler(handler)


def get_secret():
    logger.info("Retrieving secret from AWS Secrets Manager")

    try:
        client = boto3.client("secretsmanager", region_name=REGION_NAME)
        response = client.get_secret_value(SecretId=SECRET_NAME)

        try:
            secret_data = json.loads(response["SecretString"])
            # Process escaped values
            for key in secret_data:
                if isinstance(secret_data[key], str) and "\\" in secret_data[key]:
                    secret_data[key] = json.loads(f'"{secret_data[key]}"')

            return secret_data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in secret: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing secret data: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Unexpected error retrieving secret: {str(e)}")
        if DEBUG:
            logger.exception("Detailed exception info:")
        raise


class ValidationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._process_request("GET")

    def _process_request(self, method):
        if DEBUG:
            logger.debug(f"Request {method} {self.path} from {self.client_address[0]}")
            logger.debug(f"Headers: {self.headers}")

        # Path routing
        if self.path == "/pong":
            self._send_response(200, "Pong")
            return

        if self.path == "/validate":
            self._validate_headers()
            return

        self._send_response(404, "Not Found")

    def _validate_headers(self):
        try:
            secret_data = get_secret()

            if DEBUG:
                logger.debug(f"Checking {len(secret_data)} header values")

            for header, expected_value in secret_data.items():
                actual_value = self.headers.get(header)

                if DEBUG:
                    logger.debug(
                        f"Header {header}: expected={expected_value}, actual={actual_value}"
                    )

                if actual_value != expected_value:
                    logger.warning(f"Header mismatch: {header}")
                    self._send_response(403, "Authentication failed")
                    return

            if DEBUG:
                logger.debug("All headers validated successfully")

            self._send_response(200, "OK")

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            if DEBUG:
                logger.exception("Detailed exception info:")
            self._send_response(500, "Internal Server Error")

    def _send_response(self, status, message):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode())


if __name__ == "__main__":
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, ValidationHandler)

    logger.info(f"Starting validation server on port {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.server_close()
