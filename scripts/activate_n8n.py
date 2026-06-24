import requests

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlZmY2OTViNy1iZmJkLTQ4ZDgtYWIwNS0xY2UyZDJjOTdkMGEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzgyMjM1ODQ0fQ.vQAgbbV59OkYMAmnmjmwxnzGgyDaqXB32Im8fRrruSU"
WORKFLOW_ID = "GFpcvTfiJURsNbgF"
URL = f"https://n8n.xaydungbenthanh.com/api/v1/workflows/{WORKFLOW_ID}/activate"

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Accept": "application/json"
}

print(f"Activating workflow {WORKFLOW_ID}...")
res = requests.post(URL, headers=headers)
print(res.status_code)
print(res.text)
