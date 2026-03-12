"""
Rate limiting utilities for API clients.
This module enforces Spotify and Last.fm API limits via a Leaky Bucket algorithm 
to prevent our application from being temporarily banned by remote servers.
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
    This guarantees that we strictly enforce N requests per T seconds rolling window.
    Threading allows us to run multiple 'threads' concurrently within a single process.
    """
    def __init__(self, maxRequests, timeWindowSeconds, bucketId):
        self.maxRequests = maxRequests
        self.timeWindowSeconds = timeWindowSeconds
        self.bucketId = bucketId
        if maxRequests > 0:
            self.averageSpacing = timeWindowSeconds / maxRequests
        else:
            self.averageSpacing = 0
        self.lock = threading.Lock()
        
        try:
            storedTimestamps = state.getRateLimitData(self.bucketId)
            
            self.requestTimestamps = []
            
            currentTime = time.time()
            validWindowStart = currentTime - self.timeWindowSeconds
            
            self.requestTimestamps = [t for t in storedTimestamps if t > validWindowStart]
            
            if self.requestTimestamps:
                print(f"   Loaded {len(self.requestTimestamps)} recent requests for bucket '{self.bucketId}' from DB.")
                
        except Exception as e:
            print(f"Warning: Failed to load rate limit state for {self.bucketId}: {e}")
            self.requestTimestamps = []

    def _cleanOldRequests(self):
        """
        Removes timestamps outside the current rolling window.
        This reclaims capacity so subsequent requests are unblocked.
        """
        now = time.time()
        cutoff = now - self.timeWindowSeconds
        self.requestTimestamps = [t for t in self.requestTimestamps if t > cutoff]

    def _sleepWithJitter(self, waitTime, logThreshold=0.0):
        """
        Standardises jitter calculation, logging, and sleeping.
        This prevents immediate bursting when a large batch of requests wakes up simultaneously.
        """
        if waitTime <= 0:
            return
            
        jitter = waitTime * random.uniform(0.1, 0.5)
        totalWait = waitTime + jitter
        
        if totalWait > logThreshold:
            print(f"Rate Limit ({self.bucketId}): Pausing for {totalWait:.2f}s")
        
        time.sleep(totalWait)

    def acquire(self):
        """
        Blocks until a request token becomes available in the bucket.
        This is the primary gateway function to stall processing before exceeding limits.
        """
        # Ensure requests are not made faster than average spacing (leak rate)
        with self.lock:
            if self.requestTimestamps and self.averageSpacing > 0:
                lastRequestTime = self.requestTimestamps[-1]
                targetTime = lastRequestTime + self.averageSpacing
                now = time.time()
                
                if now < targetTime:
                    waitTime = targetTime - now
                    self._sleepWithJitter(waitTime, logThreshold=1.0)

            self._cleanOldRequests()
            
            # If bucket is full, wait for oldest request to expire
            while len(self.requestTimestamps) >= self.maxRequests:
                oldestTimestamp = self.requestTimestamps[0]
                now = time.time()
                waitTime = (oldestTimestamp + self.timeWindowSeconds) - now
                
                if waitTime > 0:
                    self._sleepWithJitter(waitTime, logThreshold=0.0)
                
                self._cleanOldRequests()
            
            now = time.time()
            self.requestTimestamps.append(now)
            
            try:
                state.saveRateLimitData(self.bucketId, self.requestTimestamps)
            except Exception as e:
                print(f"Warning: Failed to save rate limit state: {e}")

    # Allows LeakyBucket to be used as a context manager (in a with statement)
    def __enter__(self):
        self.acquire()
        return self

    # Allows LeakyBucket to be used as a context manager (in a with statement)
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # Allows LeakyBucket to be used as a decorator (e.g., placing @spotifyBucket above a function to rate-limit it automatically)
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        return wrapper


class RateLimitAdapter(HTTPAdapter):
    """
    A custom HTTPAdapter that handles HTTP 429 (Too Many Requests) errors and other retries.
    This guarantees we respect Retry-After headers proactively and consume LeakyBucket tokens correctly.
    """
    def __init__(self, bucket=None, *args, **kwargs):
        self.bucket = bucket
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """
        Gating mechanism for HTTP requests.
        Gate 1: Pro-active local bucket acquisition.
        Gate 2: Reactive retry handling via super().send() which leverages PrintingRetry.
        """
        if self.bucket:
            self.bucket.acquire()
        
        return super().send(request, **kwargs)

class PrintingRetry(Retry):
    """
    A subclass of Retry that prints a message to the terminal when a retry occurs.
    This gives the user visibility into transient network stalls without crashing.
    """
    def sleep(self, response=None):
        """
        Handles the wait period between retries, respecting Retry-After headers.
        Adds a safety buffer to prevent edge-case timing issues on the server.
        """
        retryAfter = self.get_retry_after(response)
        if not retryAfter:
             # Exponential backoff: backoff_factor * (2 ** (number_of_retries))
             retryAfter = self.backoff_factor * (2 ** (len(self.history)))
        
        # We add a 10s safety buffer to avoid 'off-by-one' millisecond errors on Spotify's side
        totalWait = retryAfter + 10
        print(f"   !!! Rate Limit / Error detected. Retrying in {totalWait:.2f} seconds... !!!")
        
        time.sleep(totalWait)

spotifyBucket = LeakyBucket(maxRequests=5, timeWindowSeconds=30.0, bucketId="spotifyGlobal")
lastfmBucket = LeakyBucket(maxRequests=4, timeWindowSeconds=1.0, bucketId="lastfmGlobal")

class RateLimitedSession(requests.Session):
    """
    A requests.Session subclass that enforces a LeakyBucket rate limit.
    This hooks the bucket acquisition directly into the `request` method to catch all standard HTTP calls.
    """
    def __init__(self, bucket=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket = bucket

    def request(self, method, url, *args, **kwargs):
        """
        Standard request override.
        Rate limiting is handled by the RateLimitAdapter to prevent double-acquisition.
        """
        return super().request(method, url, *args, **kwargs)

def createResilientSession(bucket, retries=3, backoffFactor=1.0):
    """
    Creates a RateLimitedSession with the RateLimitAdapter mounted.
    This allows us to handle both pro-active rate limiting (bucket) and reactive retries (adapter) in one session.
    """
    session = RateLimitedSession(bucket=None)
    
    retryStrategy = PrintingRetry(
        total=retries,
        backoff_factor=backoffFactor,
        status_forcelist=[429, 500, 502, 503],
        # Only retry on GET requests (not POST to prevent duplicates)
        allowed_methods=["GET"]
    )
    
    adapter = RateLimitAdapter(max_retries=retryStrategy, bucket=bucket)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session
