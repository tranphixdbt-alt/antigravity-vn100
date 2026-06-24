import json
import requests

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlZmY2OTViNy1iZmJkLTQ4ZDgtYWIwNS0xY2UyZDJjOTdkMGEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzgyMjM1ODQ0fQ.vQAgbbV59OkYMAmnmjmwxnzGgyDaqXB32Im8fRrruSU"
N8N_URL = "https://n8n.xaydungbenthanh.com/api/v1/workflows"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1519011980529106945/w3GqwmxlJNiLFe2MMFo4Jwanc2Bmr0FhgUw7HqJCdaLokq83EKfSYRNug58Di12mkcyW"

try:
    with open("docs/n8n_workflow_spec.json", "r") as f:
        workflow_data = json.load(f)
        
    for node in workflow_data.get("nodes", []):
        if node.get("name") == "Discord Error Alert":
            if "parameters" in node and "url" in node["parameters"]:
                node["parameters"]["url"] = DISCORD_WEBHOOK
                
    if "settings" not in workflow_data:
        workflow_data["settings"] = {}
        
    headers = {
        "X-N8N-API-KEY": API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print("Sending workflow to n8n...")
    response = requests.post(N8N_URL, headers=headers, json=workflow_data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
