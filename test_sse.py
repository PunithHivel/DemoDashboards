#!/usr/bin/env python3
"""
Test script to verify SSE streaming from author-inject endpoint
"""
import requests
import json

# Test with a small limit
url = "http://127.0.0.1:8000/author-inject/csv/upload/stream"

# Prepare form data
files = {'file': open('Result_4.csv', 'rb')}
data = {
    'organization_id': '2019',
    'limit': '3'
}

print("Starting SSE stream test...")
print(f"URL: {url}")
print(f"Params: organization_id=2019, limit=3")
print("-" * 80)

try:
    # Stream the response
    with requests.post(url, files=files, data=data, stream=True) as r:
        print(f"Status Code: {r.status_code}")
        print(f"Content-Type: {r.headers.get('content-type')}")
        print("-" * 80)
        
        event_count = 0
        for line in r.iter_lines(decode_unicode=True):
            if line:
                print(line)
                if line.startswith('data:'):
                    event_count += 1
                print()
        
        print("-" * 80)
        print(f"Total events received: {event_count}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    files['file'].close()
