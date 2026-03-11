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
            
        jitter = waitTime * random.uniform(0.1, 0.2)
        totalWait = waitTime + jitter
        
        if totalWait > logThreshold:
            print(f"Rate Limit ({self.bucketId}): Pausing for {totalWait:.2f}s")
        
        time.sleep(totalWait)

    def acquire(self):
        """
        Blocks until a request token becomes available in the bucket.
        This is the primary gateway function to stall processing before exceeding limits.
        """
        with self.lock:
            if self.requestTimestamps and self.averageSpacing > 0:
                lastRequestTime = self.requestTimestamps[-1]
                targetTime = lastRequestTime + self.averageSpacing
                now = time.time()
                
                if now < targetTime:
                    waitTime = targetTime - now
                    self._sleepWithJitter(waitTime, logThreshold=1.0)

            self._cleanOldRequests()
            
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
    A custom HTTPAdapter that handles HTTP 429 (Too Many Requests) errors and other retries.
    This guarantees we respect Retry-After headers proactively and consume LeakyBucket tokens correctly.
    """
    def __init__(self, bucket=None, *args, **kwargs):
        self.bucket = bucket
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        while True:
            try:
                response = super().send(request, **kwargs)
                
                if response.status_code == 429:
                    print("   [429] Too Many Requests. Handling retry...")
                    retryAfter = response.headers.get("Retry-After")
                    waitTime = int(retryAfter) + 1 if retryAfter else 35
                    
                    print(f"   Rate Limit 429 Hit! Sleeping for {waitTime}s...")
                    time.sleep(waitTime)
                    
                    if self.bucket:
                        self.bucket.acquire()
                        
                    continue 
                    
                if self.max_retries and hasattr(self.max_retries, 'is_retry'):
                    if response.status_code in self.max_retries.status_forcelist:
                         try:
                             retries = self.max_retries.increment(response=response)
                             retries.sleep(response) 
                             self.max_retries = retries
                             
                             if self.bucket:
                                 self.bucket.acquire()
                             continue
                         except Exception:
                             print(f"   Max retries exceeded for {response.status_code}.")
                             return response 

                return response

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"   Connection/Timeout Error: {e}")
                if self.max_retries:
                    try:
                        retries = self.max_retries.increment(error=e)
                        retries.sleep()
                        self.max_retries = retries
                        
                        if self.bucket:
                            self.bucket.acquire()
                        continue
                    except Exception as retry_err:
                        print(f"   Max retries exceeded for connection error: {retry_err}")
                        raise retry_err 
                raise e 

class PrintingRetry(Retry):
    """
    A subclass of Retry that prints a message to the terminal when a retry occurs.
    This gives the user visibility into transient network stalls without crashing.
    """
    def sleep(self, response=None):
        retryAfter = self.get_retry_after(response)
        if not retryAfter:
             retryAfter = self.backoff_factor * (2 ** (len(self.history) + 1))
        
        print(f"   !!! Rate Limit / Error detected. Retrying in {retryAfter:.2f} seconds... !!!")
        
        if retryAfter > 0:
            print(f"   [WARNING] Retry-After request detected. Sleeping for ({retryAfter:.2f}s).")
            
        time.sleep(retryAfter)

spotifyBucket = LeakyBucket(maxRequests=1, timeWindowSeconds=10.0, bucketId="spotifyGlobal")
lastfmBucket = LeakyBucket(maxRequests=5, timeWindowSeconds=1.0, bucketId="lastfmGlobal")

class RateLimitedSession(requests.Session):
    """
    A requests.Session subclass that enforces a LeakyBucket rate limit.
    This hooks the bucket acquisition directly into the `request` method to catch all standard HTTP calls.
    """
    def __init__(self, bucket=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket = bucket

    def request(self, method, url, *args, **kwargs):
        if self.bucket:
            self.bucket.acquire()
        return super().request(method, url, *args, **kwargs)

def createResilientSession(bucket, retries=3, backoffFactor=1.0):
    """
    Creates a RateLimitedSession with the RateLimitAdapter mounted.
    This allows us to handle both pro-active rate limiting (bucket) and reactive retries (adapter) in one session.
    """
    session = RateLimitedSession(bucket=bucket)
    
    retryStrategy = PrintingRetry(
        total=retries,
        backoff_factor=backoffFactor,
        status_forcelist=[429, 500, 502, 503, 504], 
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
    )
    
    adapter = RateLimitAdapter(max_retries=retryStrategy, bucket=bucket)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session
