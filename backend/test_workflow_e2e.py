"""End-to-end test for the complete workflow lifecycle.

Tests all workflow steps from initialization through completion:
  1. Register + login
  2. Create project
  3. Start workflow (initialization)
  4. Advance through every step: research -> scripting -> storyboard -> scene_planning
     -> asset_generation -> voice_generation -> subtitle_generation -> rendering
     -> thumbnail -> seo -> publishing -> completed
  5. Retry a step and verify retry_count increments
  6. Verify project status syncs with workflow step at each stage
  7. Verify workflow completion marks project as completed
  8. Test cancel workflow
  9. Verify 404s for content endpoints when no data exists yet

Usage:
  python test_workflow_e2e.py
  # or against a specific host:
  API_BASE_URL=http://localhost:8000/api/v1 python test_workflow_e2e.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_request(method: str, url: str, token: str | None = None, body: dict | None = None):
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


PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Expected step order and project status mapping
# ---------------------------------------------------------------------------
EXPECTED_STEPS = [
    "initialization",
    "research",
    "scripting",
    "storyboard",
    "scene_planning",
    "asset_generation",
    "voice_generation",
    "subtitle_generation",
    "rendering",
    "thumbnail",
    "seo",
    "publishing",
    "completed",
]

STEP_TO_PROJECT_STATUS = {
    "initialization": "researching",
    "research": "researching",
    "scripting": "scripting",
    "storyboard": "planning",
    "scene_planning": "planning",
    "asset_generation": "generating",
    "voice_generation": "generating",
    "subtitle_generation": "generating",
    "rendering": "rendering",
    "thumbnail": "rendering",
    "seo": "publishing",
    "publishing": "publishing",
    "completed": "completed",
}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
def main():
    ts = int(time.time())
    email = f"e2e_{ts}@example.com"
    username = f"e2e_{ts}"
    password = "TestPass123!"

    section("1. Authentication")
    status, resp = make_request("POST", "/auth/register", body={
        "email": email, "username": username, "password": password,
        "first_name": "E2E", "last_name": "Tester",
    })
    check("Register user", status == 201, f"got {status}")

    status, resp = make_request("POST", "/auth/login", body={"email": email, "password": password})
    check("Login", status == 200, f"got {status}")
    token = resp["access_token"]
    check("Token received", bool(token))

    # ---------------------------------------------------------------------------
    section("2. Create Project")
    status, resp = make_request("POST", "/projects", token=token, body={
        "title": "E2E Workflow Test Project",
        "description": "Testing complete workflow lifecycle",
        "content_type": "youtube_video",
        "video_style": "mixed",
        "language": "en",
        "tags": ["e2e", "test"],
    })
    check("Create project", status == 201, f"got {status}: {resp}")
    project_id = resp["id"]
    check("Project has ID", bool(project_id))
    check("Project status is draft", resp.get("status") == "draft", f"got {resp.get('status')}")
    check("Project has current_step", "current_step" in resp, f"keys: {list(resp.keys())}")

    # ---------------------------------------------------------------------------
    section("3. Start Workflow")
    status, resp = make_request("POST", f"/projects/{project_id}/workflow/start", token=token)
    check("Start workflow", status == 200, f"got {status}")
    check("Workflow current_step is initialization", resp.get("current_step") == "initialization", f"got {resp.get('current_step')}")
    check("Workflow status is running", resp.get("status") == "running", f"got {resp.get('status')}")
    check("Workflow started_at is set", bool(resp.get("started_at")), f"got {resp.get('started_at')}")
    check("Workflow retry_count is 0", resp.get("retry_count") == 0)

    # Verify project status updated
    status, resp = make_request("GET", f"/projects/{project_id}", token=token)
    check("Project status is researching after start", resp.get("status") == "researching", f"got {resp.get('status')}")
    check("Project current_step is initialization", resp.get("current_step") == "initialization", f"got {resp.get('current_step')}")

    # ---------------------------------------------------------------------------
    section("4. Verify Content Endpoints Return 404 Before Data Exists")
    status, _ = make_request("GET", f"/projects/{project_id}/research", token=token)
    check("Research 404 before data", status == 404, f"got {status}")

    status, _ = make_request("GET", f"/projects/{project_id}/script", token=token)
    check("Script 404 before data", status == 404, f"got {status}")

    status, _ = make_request("GET", f"/projects/{project_id}/storyboard", token=token)
    check("Storyboard 404 before data", status == 404, f"got {status}")

    status, _ = make_request("GET", f"/projects/{project_id}/scenes", token=token)
    check("Scenes returns empty list", status == 200, f"got {status}")

    status, _ = make_request("GET", f"/projects/{project_id}/assets", token=token)
    check("Assets returns empty list", status == 200, f"got {status}")

    status, _ = make_request("GET", f"/projects/{project_id}/jobs", token=token)
    check("Jobs returns empty list", status == 200, f"got {status}")

    # ---------------------------------------------------------------------------
    section("5. Advance Through All Workflow Steps")
    for i, expected_step in enumerate(EXPECTED_STEPS[1:], start=1):
        prev_step = EXPECTED_STEPS[i - 1]
        print(f"\n  --- Step {i}: {prev_step} -> {expected_step} ---")

        status, resp = make_request("POST", f"/projects/{project_id}/workflow/advance", token=token)
        check(f"Advance to '{expected_step}'", status == 200, f"got {status}: {resp}")
        check(f"  current_step == '{expected_step}'", resp.get("current_step") == expected_step, f"got {resp.get('current_step')}")

        # Verify project status syncs
        expected_project_status = STEP_TO_PROJECT_STATUS[expected_step]
        status, proj = make_request("GET", f"/projects/{project_id}", token=token)
        check(f"  project.status == '{expected_project_status}'", proj.get("status") == expected_project_status, f"got {proj.get('status')}")
        check(f"  project.current_step == '{expected_step}'", proj.get("current_step") == expected_step, f"got {proj.get('current_step')}")

        # Verify workflow GET returns same state
        status, wf = make_request("GET", f"/projects/{project_id}/workflow", token=token)
        check(f"  GET workflow current_step matches", wf.get("current_step") == expected_step, f"got {wf.get('current_step')}")

    # ---------------------------------------------------------------------------
    section("6. Verify Workflow Completed")
    status, wf = make_request("GET", f"/projects/{project_id}/workflow", token=token)
    check("Workflow status is completed", wf.get("status") == "completed", f"got {wf.get('status')}")
    check("Workflow completed_at is set", bool(wf.get("completed_at")))

    status, proj = make_request("GET", f"/projects/{project_id}", token=token)
    check("Project status is completed", proj.get("status") == "completed", f"got {proj.get('status')}")

    # ---------------------------------------------------------------------------
    section("7. Test Advance Beyond Final Step (should fail)")
    status, resp = make_request("POST", f"/projects/{project_id}/workflow/advance", token=token)
    check("Advance beyond completed fails", status in (400, 404, 422), f"got {status}")

    # ---------------------------------------------------------------------------
    section("8. Test Retry on a New Project")
    ts2 = int(time.time())
    email2 = f"e2e_retry_{ts2}@example.com"
    status, resp = make_request("POST", "/auth/register", body={
        "email": email2, "username": f"e2e_retry_{ts2}", "password": password,
        "first_name": "E2E", "last_name": "Retry",
    })
    status, resp = make_request("POST", "/auth/login", body={"email": email2, "password": password})
    token2 = resp["access_token"]

    status, resp = make_request("POST", "/projects", token=token2, body={
        "title": "E2E Retry Test",
        "content_type": "youtube_video",
        "video_style": "mixed",
    })
    project_id2 = resp["id"]

    # Start workflow
    status, resp = make_request("POST", f"/projects/{project_id2}/workflow/start", token=token2)
    check("Start workflow for retry test", status == 200)

    # Advance to research
    status, resp = make_request("POST", f"/projects/{project_id2}/workflow/advance", token=token2)
    check("Advance to research", resp.get("current_step") == "research", f"got {resp.get('current_step')}")

    # Retry current step
    status, resp = make_request("POST", f"/projects/{project_id2}/workflow/retry", token=token2)
    check("Retry research step", status == 200, f"got {status}")
    check("Retry count incremented to 1", resp.get("retry_count") == 1, f"got {resp.get('retry_count')}")
    check("Status is running after retry", resp.get("status") == "running", f"got {resp.get('status')}")
    check("Current step unchanged after retry", resp.get("current_step") == "research", f"got {resp.get('current_step')}")

    # Retry again
    status, resp = make_request("POST", f"/projects/{project_id2}/workflow/retry", token=token2)
    check("Retry count incremented to 2", resp.get("retry_count") == 2, f"got {resp.get('retry_count')}")

    # ---------------------------------------------------------------------------
    section("9. Test Cancel Workflow")
    status, resp = make_request("POST", f"/projects/{project_id2}/workflow/cancel", token=token2)
    check("Cancel workflow", status == 200, f"got {status}")

    status, wf = make_request("GET", f"/projects/{project_id2}/workflow", token=token2)
    check("Workflow status is cancelled", wf.get("status") == "cancelled", f"got {wf.get('status')}")

    status, proj = make_request("GET", f"/projects/{project_id2}", token=token2)
    check("Project status is cancelled", proj.get("status") == "cancelled", f"got {proj.get('status')}")

    # Try to advance after cancel (should fail)
    status, _ = make_request("POST", f"/projects/{project_id2}/workflow/advance", token=token2)
    check("Advance after cancel fails", status in (400, 404, 422), f"got {status}")

    # ---------------------------------------------------------------------------
    section("10. Test Start Workflow on Already-Completed Project (should fail or re-create)")
    status, resp = make_request("POST", f"/projects/{project_id}/workflow/start", token=token)
    # The service allows starting a new workflow if the existing one is not RUNNING
    # Since the first workflow is COMPLETED, this should either succeed or raise
    if status == 200:
        check("Re-start workflow on completed project succeeds", True)
        check("New workflow starts at initialization", resp.get("current_step") == "initialization", f"got {resp.get('current_step')}")
    else:
        check("Re-start workflow on completed project rejected", status in (400, 409, 422), f"got {status}")

    # ---------------------------------------------------------------------------
    # Summary
    section("SUMMARY")
    total = PASS + FAIL
    print(f"  Total: {total}  Pass: {PASS}  Fail: {FAIL}")
    if FAIL > 0:
        print(f"\n  !! {FAIL} TESTS FAILED !!")
        sys.exit(1)
    else:
        print("\n  ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
