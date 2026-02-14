"""
Rate limiting utilities for API clients.

Includes a Leaky Bucket implementation and a custom Requests adapter for handling 429 errors.
"""
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import threading
from functools import wraps

class LeakyBucket:
    """
    A thread-safe Leaky Bucket rate limiter implementation.

    Enforces a strict limit of N requests per T seconds rolling window.
    """
    def __init__(self, max_requests, time_window_seconds):
        self.max_requests = max_requests
        self.time_window_seconds = time_window_seconds
        self.request_timestamps = []
        self.lock = threading.Lock()

    def _clean_old_requests(self):
        """Remove timestamps outside the current rolling window."""
        now = time.perf_counter()
        cutoff = now - self.time_window_seconds
        self.request_timestamps = [t for t in self.request_timestamps if t > cutoff]

    def acquire(self):
        """Block until a request token is available in the bucket."""
        with self.lock:
            self._clean_old_requests()
            
            while len(self.request_timestamps) >= self.max_requests:
                # Calculate wait time
                # We need to wait until the oldest request expires
                oldest_timestamp = self.request_timestamps[0]
                now = time.perf_counter()
                wait_time = (oldest_timestamp + self.time_window_seconds) - now
                
                if wait_time > 0:
                    print(f"Rate Limit: Pausing for {wait_time:.2f}s...")
                    time.sleep(wait_time)
                
                # Re-clean after waking up to be sure
                self._clean_old_requests()
            
            # Add current timestamp
            self.request_timestamps.append(time.perf_counter())

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        return wrapper


class RateLimitAdapter(HTTPAdapter):
    """
    A custom HTTPAdapter that handles HTTP 429 (Too Many Requests).

    Respects the 'Retry-After' header.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        while True:
            try:
                response = super().send(request, **kwargs)
                
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    
                    if retry_after:
                        wait_time = int(retry_after) + 1 # Add 1s buffer
                        print(f"Rate Limit 429 Hit! Sleeping for {wait_time}s (per Spotify instruction)...")
                        time.sleep(wait_time)
                        continue # Retry the request
                                    
                return response
            except Exception as e:
                # Check for connection errors that look like rate limits or closed connections?
                raise e

class PrintingRetry(Retry):
    """
    A subclass of Retry that prints a message to the terminal when a retry occurs.
    """
    def sleep(self, response=None):
        retry_after = self.get_retry_after(response)
        if not retry_after:
            retry_after = self.backoff_factor * (2 ** (len(self.history) + 1))
        
        print(f"   !!! Rate Limit / Error detected. Retrying in {retry_after:.2f} seconds... !!!")
        super().sleep(response)

def create_resilient_session(retries=3, backoff_factor=1.0):
    """
    Create a requests.Session with the RateLimitAdapter mounted.
    """
    session = requests.Session()
    
    # Use custom PrintingRetry for visibility
    retry_strategy = PrintingRetry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504], # Added 429 here to let urllib3 handle it natively too
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
    )
    
    adapter = RateLimitAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session
