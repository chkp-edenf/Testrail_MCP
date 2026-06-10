"""Base HTTP client for TestRail API"""

import asyncio
import base64
import logging
import sys
from typing import Optional, Any, Dict
import httpx
from pydantic import BaseModel

from .exceptions import (
    TestRailError,
    TestRailAPIError,
    TestRailTimeoutError,
    TestRailNetworkError,
    TestRailAuthenticationError,
    TestRailPermissionError,
    TestRailNotFoundError,
    TestRailBadRequestError,
    TestRailRateLimitError,
    TestRailServerError
)

logger = logging.getLogger(__name__)

# Maximum upstream response body length to include in error log lines.
# Bodies can echo back request URLs (which may contain a redirected
# Authorization header in misconfigured setups) and other operator-
# sensitive content. The full body remains on the raised exception's
# `response_data` for callers that need it — only the log line is
# truncated. spektr v2.0 MEDIUM.
_ERROR_LOG_BODY_MAX = 500


def _trunc_for_log(value: object, limit: int = _ERROR_LOG_BODY_MAX) -> str:
    """Stringify and truncate a value for inclusion in a single log line."""
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated, {len(text) - limit} more chars]"


class ClientConfig(BaseModel):
    """Configuration for TestRail API client"""
    base_url: str
    username: str
    api_key: str
    timeout: int = 30


class BaseAPIClient:
    """Base HTTP client with authentication and error handling"""
    
    # Retry configuration for GET requests only (v1.4.0)
    # Exponential backoff: 1s → 2s → 4s for transient failures
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF_FACTOR = 2.0
    
    def __init__(self, config: ClientConfig, rate_limiter=None):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.rate_limiter = rate_limiter  # Injected rate limiter
        # Create Basic Auth header
        auth_string = f"{config.username}:{config.api_key}"
        auth_bytes = auth_string.encode("utf-8")
        auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
        self._headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        # Create persistent HTTP client (reused across all requests)
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=self._headers,
            follow_redirects=True  # Match axios default behavior
        )
    
    async def close(self):
        """Close the HTTP client connection"""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make authenticated API request with error handling, rate limiting, and retry logic for GET requests"""
        # Import metrics tracking
        try:
            from ...server.api.metrics import record_request_success, record_request_failure
            metrics_available = True
        except ImportError:
            metrics_available = False
        
        # Apply rate limiting if configured
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        # base_url ends with /index.php from normalization
        # TestRail uses format: index.php?/api/v2/endpoint&param1=value1&param2=value2
        url = f"{self.base_url}?/api/v2/{endpoint}"
        
        # Manually append params with & since TestRail's URL format is non-standard
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}&{param_str}"
        
        # Determine if this operation should retry (GET only)
        should_retry = method.upper() == "GET"
        max_attempts = self.MAX_RETRIES if should_retry else 1
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(url)
                elif method.upper() == "POST":
                    response = await self._client.post(url, json=data)
                elif method.upper() == "PUT":
                    response = await self._client.put(url, json=data)
                elif method.upper() == "DELETE":
                    response = await self._client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                # Record successful request
                if metrics_available:
                    record_request_success()
                
                if response.text and response.text.strip():
                    return response.json()
                return []
                    
            except httpx.TimeoutException as e:
                logger.error(f"⏱️ Timeout on {method} {endpoint}")
                last_exception = TestRailTimeoutError(f"Request timed out after {self.config.timeout}s")
                
                # Retry on timeout for GET requests only
                if should_retry and attempt < max_attempts - 1:
                    retry_delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_FACTOR ** attempt)
                    logger.warning("[RETRY] Attempt %d/%d failed: TimeoutException. Retrying in %ss...", attempt + 1, self.MAX_RETRIES, retry_delay)
                    await asyncio.sleep(retry_delay)
                    continue
                
                # Record failure before raising
                if metrics_available:
                    record_request_failure()
                raise last_exception
                
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                response_text = e.response.text
                
                # Try to extract error message from response
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", response_text)
                except:
                    error_data = {"raw_response": response_text}
                    error_message = response_text
                
                logger.error(
                    "HTTP %s on %s %s: %s",
                    status,
                    method,
                    endpoint,
                    _trunc_for_log(error_message),
                )
                
                # Raise specific error based on status code
                if status == 400:
                    last_exception = TestRailBadRequestError(f"Bad Request: {error_message}", error_data)
                elif status == 401:
                    last_exception = TestRailAuthenticationError(f"Authentication failed: {error_message}", error_data)
                elif status == 403:
                    last_exception = TestRailPermissionError(f"Permission denied: {error_message}", error_data)
                elif status == 404:
                    last_exception = TestRailNotFoundError(f"Resource not found: {error_message}", error_data)
                elif status == 429:
                    last_exception = TestRailRateLimitError(f"Rate limit exceeded: {error_message}", error_data)
                    
                    # Retry on rate limit for GET requests only
                    if should_retry and attempt < max_attempts - 1:
                        # Check for Retry-After header
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                retry_delay = float(retry_after)
                            except ValueError:
                                # If Retry-After is not a number, use exponential backoff
                                retry_delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_FACTOR ** attempt)
                        else:
                            retry_delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_FACTOR ** attempt)
                        logger.warning("[RETRY] Attempt %d/%d failed: 429 Too Many Requests. Retrying in %ss...", attempt + 1, self.MAX_RETRIES, retry_delay)
                        await asyncio.sleep(retry_delay)
                        continue
                    raise last_exception
                elif status >= 500:
                    last_exception = TestRailServerError(status, f"Server error: {error_message}", error_data)
                    
                    # Retry on server errors for GET requests only
                    if should_retry and attempt < max_attempts - 1:
                        retry_delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_FACTOR ** attempt)
                        logger.warning("[RETRY] Attempt %d/%d failed: %s Server Error. Retrying in %ss...", attempt + 1, self.MAX_RETRIES, status, retry_delay)
                        await asyncio.sleep(retry_delay)
                        continue
                    raise last_exception
                else:
                    last_exception = TestRailAPIError(status, f"API error: {error_message}", error_data)
                
                # Record failure before raising for non-retryable HTTP errors
                if metrics_available:
                    record_request_failure()
                raise last_exception
            
            except httpx.NetworkError as e:
                logger.error(f"🔌 Network error on {method} {endpoint}: {str(e)}")
                last_exception = TestRailNetworkError(f"Network error: {str(e)}")
                
                # Retry on network errors for GET requests only
                if should_retry and attempt < max_attempts - 1:
                    retry_delay = self.INITIAL_RETRY_DELAY * (self.RETRY_BACKOFF_FACTOR ** attempt)
                    logger.warning("[RETRY] Attempt %d/%d failed: NetworkError. Retrying in %ss...", attempt + 1, self.MAX_RETRIES, retry_delay)
                    await asyncio.sleep(retry_delay)
                    continue
                
                # Record failure before raising
                if metrics_available:
                    record_request_failure()
                raise last_exception
                
            except TestRailError:
                # Re-raise our custom errors (non-retryable)
                raise
                
            except Exception as e:
                logger.error(
                    "Unexpected error on %s %s: %s",
                    method,
                    endpoint,
                    _trunc_for_log(e),
                )
                if metrics_available:
                    record_request_failure()
                # `raise ... from e` preserves the original traceback so
                # operators can see the underlying cause in logs. spektr
                # v2.0 LOW.
                raise TestRailError(f"Unexpected error: {_trunc_for_log(e)}") from e
        
        # Should not reach here, but raise last exception if we do
        if last_exception:
            if metrics_available:
                record_request_failure()
            raise last_exception
    
    async def upload_file(self, endpoint: str, file_data: bytes, filename: str) -> Any:
        """Upload a file to a TestRail endpoint (multipart/form-data).

        Used by the Attachments API for uploading screenshots, documents, etc.
        """
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        url = f"{self.base_url}?/api/v2/{endpoint}"

        # Build multipart upload with auth header only.
        # Must use a separate httpx request (not self._client) because the
        # persistent client has Content-Type: application/json as a default
        # header which prevents httpx from auto-setting the multipart boundary.
        auth_header = {k: v for k, v in self._headers.items() if k.lower() == "authorization"}
        files = {"attachment": (filename, file_data)}

        try:
            from ...server.api.metrics import record_request_success, record_request_failure
            metrics_available = True
        except ImportError:
            metrics_available = False

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as upload_client:
                response = await upload_client.post(url, files=files, headers=auth_header)
            response.raise_for_status()
            if metrics_available:
                record_request_success()
            if response.text and response.text.strip():
                return response.json()
            return {}
        except httpx.HTTPStatusError as e:
            if metrics_available:
                record_request_failure()
            status = e.response.status_code
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", e.response.text)
            except Exception:
                error_message = e.response.text
            if status == 401:
                raise TestRailAuthenticationError(f"Authentication failed: {error_message}")
            elif status == 403:
                raise TestRailPermissionError(f"Permission denied: {error_message}")
            elif status == 404:
                raise TestRailNotFoundError(f"Resource not found: {error_message}")
            else:
                raise TestRailAPIError(status, f"Upload failed: {error_message}")
        except httpx.TimeoutException:
            if metrics_available:
                record_request_failure()
            raise TestRailTimeoutError(f"Upload timed out after {self.config.timeout}s")
        except httpx.NetworkError as e:
            if metrics_available:
                record_request_failure()
            raise TestRailNetworkError(f"Network error during upload: {str(e)}")

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request"""
        return await self._request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Any:
        """POST request"""
        return await self._request("POST", endpoint, data=data)
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Any:
        """PUT request"""
        return await self._request("PUT", endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Any:
        """DELETE request"""
        return await self._request("DELETE", endpoint)
