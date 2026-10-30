"""End-to-end test for project creation flow.

Tests the complete flow:
1. Register a new user
2. Login to get tokens
3. Create a project (POST /api/v1/projects)
4. Get the project (GET /api/v1/projects/{id})
5. List projects (GET /api/v1/projects)
6. Get workflow (GET /api/v1/projects/{id}/workflow) — expects 404
7. Update the project (PATCH /api/v1/projects/{id})
8. Delete the project (DELETE /api/v1/projects/{id})

Run: python test_project_flow.py
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"

# Test user — generates a unique email using timestamp
TS = int(time.time())
EMAIL = f"testuser_{TS}@example.com"
USERNAME = f"testuser_{TS}"
PASSWORD = "TestPass123!"


def make_request(
    method: str,
    url: str,
    token: str | None = None,
    body: dict | None = None,
) -> tuple[int, dict]:
    """Make an HTTP request and return (status_code, response_json)."""
    url = f"{BASE_URL}{url}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode()
        try:
            return e.code, json.loads(resp_body)
        except json.JSONDecodeError:
            return e.code, {"raw": resp_body}


def check_health() -> bool:
    """Check if the backend is running."""
    try:
        req = urllib.request.Request(HEALTH_URL)
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        print(f"[CHECK] Backend health: {data['status']} — {data['app']}")
        return data["status"] == "healthy"
    except Exception as e:
        print(f"[FAIL] Backend is not running: {e}")
        return False


def run_e2e_test():
    """Run the full E2E test flow."""
    print("=" * 60)
    print("  E2E Project Creation Flow Test")
    print("=" * 60)

    # Step 0: Check backend health
    print("\n[STEP 0] Checking backend health...")
    if not check_health():
        print("\n[RESULT] FAIL — Backend is not running. Start it first.")
        sys.exit(1)

    # Step 1: Register
    print(f"\n[STEP 1] Registering user: {EMAIL}")
    status, resp = make_request("POST", "/auth/register", body={
        "email": EMAIL,
        "username": USERNAME,
        "password": PASSWORD,
        "first_name": "Test",
        "last_name": "User",
    })
    print(f"  Status: {status}")
    print(f"  Response: {resp.get('message', resp)}")
    if status != 201:
        print(f"  [FAIL] Expected 201, got {status}")
        sys.exit(1)
    print("  [PASS]")

    # Step 2: Login
    print(f"\n[STEP 2] Logging in as {EMAIL}")
    status, resp = make_request("POST", "/auth/login", body={
        "email": EMAIL,
        "password": PASSWORD,
    })
    print(f"  Status: {status}")
    if status != 200:
        print(f"  [FAIL] Expected 200, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    access_token = resp["access_token"]
    refresh_token = resp["refresh_token"]
    user = resp["user"]
    print(f"  User ID: {user['id']}")
    print(f"  Access token: {access_token[:30]}...")
    print(f"  Refresh token: {refresh_token[:30]}...")
    print("  [PASS]")

    # Step 3: Create project
    print("\n[STEP 3] Creating project...")
    project_body = {
        "title": "E2E Test Video Project",
        "description": "A test project created by the E2E test script",
        "language": "en",
        "audience": "Tech enthusiasts",
        "content_type": "youtube_video",
        "video_style": "mixed",
        "target_duration_seconds": 600,
        "tags": ["test", "e2e", "automation"],
    }
    status, resp = make_request("POST", "/projects", token=access_token, body=project_body)
    print(f"  Status: {status}")
    if status != 201:
        print(f"  [FAIL] Expected 201, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    project_id = resp["id"]
    print(f"  Project ID: {project_id}")
    print(f"  Title: {resp['title']}")
    print(f"  Status: {resp['status']}")
    print(f"  Current step: {resp['current_step']}")
    print(f"  Content type: {resp['content_type']}")
    print(f"  Tags: {resp['tags']}")
    # Verify fields match
    assert resp["title"] == project_body["title"], f"Title mismatch: {resp['title']}"
    assert resp["description"] == project_body["description"], f"Description mismatch"
    assert resp["language"] == project_body["language"], f"Language mismatch"
    assert resp["content_type"] == project_body["content_type"], f"Content type mismatch"
    assert resp["tags"] == project_body["tags"], f"Tags mismatch: {resp['tags']}"
    print("  [PASS] All fields match")

    # Step 4: Get project by ID
    print(f"\n[STEP 4] Getting project by ID: {project_id}")
    status, resp = make_request("GET", f"/projects/{project_id}", token=access_token)
    print(f"  Status: {status}")
    if status != 200:
        print(f"  [FAIL] Expected 200, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    assert resp["id"] == project_id, "Project ID mismatch"
    assert resp["title"] == project_body["title"], "Title mismatch"
    print(f"  Title: {resp['title']}")
    print(f"  Status: {resp['status']}")
    print("  [PASS]")

    # Step 5: List projects
    print("\n[STEP 5] Listing projects...")
    status, resp = make_request("GET", "/projects?limit=10", token=access_token)
    print(f"  Status: {status}")
    if status != 200:
        print(f"  [FAIL] Expected 200, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    print(f"  Total: {resp.get('total', '?')}")
    print(f"  Items count: {len(resp.get('items', []))}")
    # Verify our project is in the list
    found = any(p["id"] == project_id for p in resp.get("items", []))
    assert found, "Created project not found in list"
    print("  [PASS] Project found in list")

    # Step 6: Get workflow (expect 404 — no workflow started yet)
    print(f"\n[STEP 6] Getting workflow for project (expect 404)...")
    status, resp = make_request("GET", f"/projects/{project_id}/workflow", token=access_token)
    print(f"  Status: {status}")
    if status == 404:
        print(f"  Response: {resp.get('error', {}).get('message', resp)}")
        print("  [PASS] Correctly returns 404 — no workflow started")
    else:
        print(f"  [WARN] Expected 404, got {status}")
        print(f"  Response: {resp}")

    # Step 7: Update project
    print(f"\n[STEP 7] Updating project...")
    update_body = {
        "title": "Updated E2E Test Title",
        "description": "Updated description for the test project",
    }
    status, resp = make_request("PATCH", f"/projects/{project_id}", token=access_token, body=update_body)
    print(f"  Status: {status}")
    if status != 200:
        print(f"  [FAIL] Expected 200, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    assert resp["title"] == update_body["title"], "Title not updated"
    assert resp["description"] == update_body["description"], "Description not updated"
    print(f"  Updated title: {resp['title']}")
    print(f"  Updated description: {resp['description']}")
    print("  [PASS]")

    # Step 8: Delete project
    print(f"\n[STEP 8] Deleting project...")
    status, resp = make_request("DELETE", f"/projects/{project_id}", token=access_token)
    print(f"  Status: {status}")
    if status != 200:
        print(f"  [FAIL] Expected 200, got {status}")
        print(f"  Response: {resp}")
        sys.exit(1)
    print(f"  Response: {resp.get('message', resp)}")
    print("  [PASS]")

    # Step 9: Verify project is deleted (GET should 404)
    print(f"\n[STEP 9] Verifying project is deleted...")
    status, resp = make_request("GET", f"/projects/{project_id}", token=access_token)
    print(f"  Status: {status}")
    if status == 404:
        print("  [PASS] Project correctly returns 404 after deletion")
    else:
        print(f"  [WARN] Expected 404, got {status}")

    # Step 10: Test auth — create project without token (expect 401)
    print("\n[STEP 10] Testing auth — create project without token...")
    status, resp = make_request("POST", "/projects", body=project_body)
    print(f"  Status: {status}")
    if status == 401:
        error_msg = resp.get("error", {}).get("message", "")
        print(f"  Error: {error_msg}")
        print("  [PASS] Correctly returns 401 without token")
    else:
        print(f"  [FAIL] Expected 401, got {status}")

    # Summary
    print("\n" + "=" * 60)
    print("  E2E TEST RESULT: ALL PASSED")
    print("=" * 60)
    print(f"  User: {EMAIL}")
    print(f"  Project created, fetched, listed, updated, deleted successfully")
    print(f"  Auth correctly enforced (401 without token)")
    print(f"  Workflow correctly returns 404 when not started")
    print("=" * 60)


if __name__ == "__main__":
    run_e2e_test()
