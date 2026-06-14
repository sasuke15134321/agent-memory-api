import requests
import json

BASE_URL = "http://localhost:8000"

def test_search_result_trust_check():
    """Test the search result trust check endpoint"""
    payload = {
        "agent_id": "test-agent",
        "result_type": "operational_log",
        "source": {
            "name": "monitoring-system",
            "source_type": "system_log",
            "trust_level": "high"
        },
        "freshness": {
            "status": "current",
            "max_age_seconds": 300
        },
        "provenance": {
            "system_generated": True
        },
        "intended_use": "summarization",
        "policy": {
            "deny_stale_results": True,
            "require_review_on_conflict": True
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/search-result-trust/check", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    data = response.json()
    assert "trust_check_id" in data
    assert "decision" in data
    assert data["decision"] in ["allow", "deny", "review_required"]
    assert "evidence" in data
    assert "evidence_id" in data["evidence"]

if __name__ == "__main__":
    test_search_result_trust_check()
    print("✅ Test passed!")
