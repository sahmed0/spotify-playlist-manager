"""
Rate limiting utilities for API clients.

Includes a Leaky Bucket implementation and a custom Requests adapter for handling 429 errors.
"""
import time
import random
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import threading
from functools import wraps
import app_state as state

class LeakyBucket:
    """
    A thread-safe Leaky Bucket rate limiter implementation with database persistence.

    Enforce a strict limit of N requests per T seconds rolling window.
    """
    def __init__(self, max_requests, time_window_seconds, bucket_id):
        self.max_requests = max_requests
        self.time_window_seconds = time_window_seconds
        self.bucket_id = bucket_id
        self.lock = threading.Lock()
        
        # Load state from DB
        try:
            stored_timestamps = state.get_rate_limit_data(self.bucket_id)
            # Filter out old timestamps immediately
            
            self.request_timestamps = []
            
            current_time = time.time()
            valid_window_start = current_time - self.time_window_seconds
            
            self.request_timestamps = [t for t in stored_timestamps if t > valid_window_start]
            
            if self.request_timestamps:
                print(f"   Loaded {len(self.request_timestamps)} recent requests for bucket '{self.bucket_id}' from DB.")
                
        except Exception as e:
            print(f"Warning: Failed to load rate limit state for {self.bucket_id}: {e}")
            self.request_timestamps = []

    def _clean_old_requests(self):
        """Remove timestamps outside the current rolling window."""
        now = time.time()
        cutoff = now - self.time_window_seconds
        self.request_timestamps = [t for t in self.request_timestamps if t > cutoff]

    def acquire(self):
        """Block until a request token becomes available in the bucket."""
        with self.lock:
            self._clean_old_requests()
            
            while len(self.request_timestamps) >= self.max_requests:
                # Calculate wait time
                oldest_timestamp = self.request_timestamps[0]
                now = time.time()
                wait_time = (oldest_timestamp + self.time_window_seconds) - now
                
                if wait_time > 0:
                    jitter = random.uniform(2, 5)
                    total_wait = wait_time + jitter
                    print(f"Rate Limit ({self.bucket_id}): Pausing for {total_wait:.2f}s (incl. {jitter:.2f}s jitter)...")
                    time.sleep(total_wait)
                
                # Re-clean after waking up
                self._clean_old_requests()
            
            # Add current timestamp
            now = time.time()
            self.request_timestamps.append(now)
            
            # Save state
            try:
                state.save_rate_limit_data(self.bucket_id, self.request_timestamps)
            except Exception as e:
                # Don't crash on DB error, just warn
                print(f"Warning: Failed to save rate limit state: {e}")

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
    A custom HTTPAdapter that handles HTTP 429 (Too Many Requests) errors.

    Respect the 'Retry-After' header provided by the server.
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
                        wait_time = int(retry_after) + 30 # Add 30s buffer
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
        
        if retry_after > 300:
            print(f"   [WARNING] Long retry time detected ({retry_after:.2f}s). Sleeping instead of exiting.")
            # Optional: can exit rather than sleep:
            # import sys
            # sys.exit(1)
            
        super().sleep(response)

# Shared bucket instance (Global Rate Limiter for Spotify)
# VERY CAREFUL LIMIT: 1 request per 30 seconds (Ironclad Safety)
shared_bucket = LeakyBucket(max_requests=1, time_window_seconds=30.0, bucket_id="spotify_global")

# Dedicated bucket for Last.fm (Safe but faster: 4 requests per second)
lastfm_bucket = LeakyBucket(max_requests=4, time_window_seconds=1.0, bucket_id="lastfm_global")

class RateLimitedSession(requests.Session):
    """
    A requests.Session subclass that enforces a LeakyBucket rate limit.
    """
    def __init__(self, bucket=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket = bucket

    def request(self, method, url, *args, **kwargs):
        if self.bucket:
            self.bucket.acquire()
        return super().request(method, url, *args, **kwargs)

def create_resilient_session(retries=3, backoff_factor=1.0, bucket=None):
    """
    Create a RateLimitedSession with the RateLimitAdapter mounted.
    
    Args:
        bucket (LeakyBucket): The rate limiter bucket to use. Defaults to shared_bucket (Spotify) if None.
    """
    if bucket is None:
        bucket = shared_bucket
        
    session = RateLimitedSession(bucket=bucket)
    
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
