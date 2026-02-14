import unittest
from unittest.mock import MagicMock, patch
import time
from rate_limiter import LeakyBucket, RateLimitAdapter
import requests

class TestRateLimiter(unittest.TestCase):
    def test_leaky_bucket_timing(self):
        """Verify that LeakyBucket enforces the time window."""
        # limit: 2 requests per 1 second
        bucket = LeakyBucket(max_requests=2, time_window_seconds=1.0)
        
        start_time = time.perf_counter()
        
        print("Acquiring 1...")
        bucket.acquire() # 1st - immediate
        print("Acquiring 2...")
        bucket.acquire() # 2nd - immediate
        
        print("Acquiring 3 (Should Pause)...")
        bucket.acquire() # 3rd - Should wait until window clears (approx 1s from start)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"Total duration for 3 requests (limit 2/1s): {duration:.4f}s")
        
        self.assertGreaterEqual(duration, 1.0)
        self.assertLess(duration, 1.2) # Allow some overhead

    @patch('requests.adapters.HTTPAdapter.send')
    def test_rate_limit_adapter_retry_after(self, mock_send):
        """Verify that RateLimitAdapter respects Retry-After header."""
        adapter = RateLimitAdapter()
        session = requests.Session()
        session.mount('https://', adapter)
        
        # Mock Response 1: 429 with Retry-After: 1
        resp_429 = requests.Response()
        resp_429.status_code = 429
        resp_429.headers['Retry-After'] = '1'
        
        # Mock Response 2: 200 OK
        resp_200 = requests.Response()
        resp_200.status_code = 200
        
        # The adapter calls super().send(). We mock that to return 429 first, then 200.
        mock_send.side_effect = [resp_429, resp_200]
        
        start_time = time.perf_counter()
        print("Sending request (expecting 429 -> sleep -> 200)...")
        response = session.get("https://example.com/api")
        end_time = time.perf_counter()
        
        print(f"Request duration: {end_time - start_time:.4f}s")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 2)
        # Should have slept for 1s + 1s buffer = 2s
        self.assertGreaterEqual(end_time - start_time, 2.0)

if __name__ == '__main__':
    unittest.main()
