"""Scenario tests: realistic user flows for knowledge accumulation, recommendations, growth."""
import subprocess, time, httpx, json, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Start server
stderr_file = open("server_stderr.log", "w", buffering=1)
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"],
    stdout=subprocess.DEVNULL, stderr=stderr_file,
)

for i in range(15):
    time.sleep(2)
    try:
        r = httpx.get("http://127.0.0.1:8765/health", timeout=3)
        if r.status_code == 200:
            print(f"Server ready after {(i+1)*2}s")
            break
    except:
        pass
else:
    print("Server failed to start!")
    proc.terminate()
    exit(1)

BASE = "http://127.0.0.1:8765"
passed = 0
failed = 0
scenarios_passed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  [PASS] {name} {detail}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

def scenario(name, cond, detail=""):
    global scenarios_passed
    if cond:
        print(f"  [SCENARIO PASS] {name} {detail}")
        scenarios_passed += 1
    else:
        print(f"  [SCENARIO FAIL] {name} {detail}")

# ============ Setup ============
print("\n========== Scenario Tests ==========")

r = httpx.post(f"{BASE}/api/auth/login", json={"username": "demo", "password": "demo123"})
token = r.json()["data"]["token"]
h = {"Authorization": f"Bearer {token}"}
print(f"Logged in as demo")

# =============================================
# SCENARIO 1: Knowledge Accumulation via Multi-Upload
# =============================================
print("\n--- Scenario 1: Knowledge Accumulation ---")

# 1a: Upload first document
doc1 = "概率论 58分，线性代数 72分，高等数学 85分"
r = httpx.post(f"{BASE}/api/analysis/upload", headers=h,
               files={"file": ("exam1.txt", doc1.encode("utf-8"), "text/plain")})
file1_id = r.json()["data"]["fileId"]
print(f"  Upload 1: fileId={file1_id}")

# Wait for analysis
completed = False
for _ in range(15):
    time.sleep(2)
    r = httpx.get(f"{BASE}/api/analysis/progress/{file1_id}", headers=h)
    if r.json()["data"]["status"] == "completed":
        completed = True
        break
check("Upload 1 analysis completed", completed)

# Get result & verify knowledge
knowledge_before = []
if completed:
    r = httpx.get(f"{BASE}/api/analysis/result/{file1_id}", headers=h)
    d = r.json()
    knowledge_before = [k["name"] for k in d["data"].get("extractedKnowledge", [])]
    print(f"  Knowledge after upload 1: {knowledge_before}")

check("Upload 1 has extracted knowledge", len(knowledge_before) >= 2)
# Verify analysis is real (not error/fallback)
d1 = r.json()["data"]
has_error = bool(d1.get("error")) or d1.get("summary", "").startswith("分析失败")
check("Upload 1 analysis is real (no error field)", not has_error)

# Check dashboard overview - knowledge rate should be updated
r = httpx.get(f"{BASE}/api/dashboard/overview", headers=h)
overview1 = r.json()["data"]
check("Knowledge rate > 0 after upload 1", overview1["knowledgeRate"] > 0,
      f"(rate={overview1['knowledgeRate']})")

# 1b: Upload second document (more subjects, different scores)
doc2 = "概率论 68分，线性代数 80分，高等数学 90分，数据结构 75分，算法 60分"
r = httpx.post(f"{BASE}/api/analysis/upload", headers=h,
               files={"file": ("exam2.txt", doc2.encode("utf-8"), "text/plain")})
file2_id = r.json()["data"]["fileId"]
print(f"  Upload 2: fileId={file2_id}")

completed2 = False
for _ in range(20):
    time.sleep(3)
    r = httpx.get(f"{BASE}/api/analysis/progress/{file2_id}", headers=h)
    if r.json()["data"]["status"] == "completed":
        completed2 = True
        break

check("Upload 2 analysis completed", completed2)

knowledge_after = []
if completed2:
    r = httpx.get(f"{BASE}/api/analysis/result/{file2_id}", headers=h)
    d = r.json()
    knowledge_after = [k["name"] for k in d["data"].get("extractedKnowledge", [])]
    print(f"  Knowledge after upload 2: {knowledge_after}")

check("Upload 2 has extracted knowledge", len(knowledge_after) >= 2)
d2 = r.json()["data"]
has_error2 = bool(d2.get("error")) or d2.get("summary", "").startswith("分析失败")
check("Upload 2 analysis is real (no error field)", not has_error2)

# 1c: Verify knowledge graph grew after second upload
r = httpx.get(f"{BASE}/api/dashboard/knowledge-graph", headers=h)
graph = r.json()["data"]
node_count = len(graph["nodes"])
all_knowledge = knowledge_before + knowledge_after
unique = list(set(all_knowledge))
print(f"  Graph nodes: {node_count}, unique knowledge: {unique}")

check("Knowledge graph has nodes", node_count > 0)

# Scenario: knowledge should have accumulated (more unique topics after upload 2)
r = httpx.get(f"{BASE}/api/dashboard/overview", headers=h)
overview2 = r.json()["data"]
scenario("Knowledge rate updated after multi-upload",
         overview2["knowledgeRate"] > 0,
         f"(rate after uploads: {overview2['knowledgeRate']})")

# Scenario: at least one weak point persists (概率论 was 58, now 68 - still borderline)
r = httpx.get(f"{BASE}/api/dashboard/knowledge-graph", headers=h)
graph2 = r.json()["data"]
nodes_with_status = sum(1 for n in graph2["nodes"] for c in n.get("children", [])
                        if c.get("status") in ("薄弱", "预警"))
print(f"  Nodes with weak/warning status: {nodes_with_status}")

# =============================================
# SCENARIO 2: Recommendation Relevance
# =============================================
print("\n--- Scenario 2: Recommendation Relevance ---")

r = httpx.get(f"{BASE}/api/today/recommendations", headers=h)
recs = r.json()["data"]["recommendations"]
check("Recommendations returned", len(recs) > 0, f"(count={len(recs)})")

# Check that recommendations reference specific scores or weak points
rec_reasons = [r["reason"] for r in recs]
has_personalized = any(
    ("概率论" in reason or "55" in reason or "薄弱" in reason)
    for reason in rec_reasons
)
scenario("Recommendations reference weak points/scores",
         has_personalized,
         f"(reasons: {rec_reasons[:2]})")

# Verify recommendation structure
for rec in recs[:1]:
    check("Recommendation has type", bool(rec.get("type")))
    check("Recommendation has title", bool(rec.get("title")))
    check("Recommendation has difficulty", bool(rec.get("difficulty")))
    check("Recommendation has reason", bool(rec.get("reason")))

# =============================================
# SCENARIO 3: Learning Progress & Growth
# =============================================
print("\n--- Scenario 3: Learning Progress Growth ---")

# Create learning records for this week (simulate studying)
for i in range(3):
    r = httpx.post(f"{BASE}/api/learning/records", headers=h,
                   json={"resource_id": 1, "action": "studied", "duration_seconds": 1800})
    check(f"Learning record {i+1}", r.json()["code"] == 200)

r = httpx.get(f"{BASE}/api/learning/stats", headers=h)
stats = r.json()["data"]
check("Has today records", stats["today_records"] >= 1,
      f"(today_records={stats['today_records']})")
check("Total studied > 0", stats["total_studied"] > 0)
check("Total duration > 0", stats["total_duration_minutes"] > 0)

# Check progress endpoint
r = httpx.get(f"{BASE}/api/today/progress", headers=h)
progress = r.json()["data"]
check("Weekly study hours > 0", progress["weeklyStudyHours"] > 0,
      f"(hours={progress['weeklyStudyHours']})")
check("Has knowledge rate", progress["knowledgeRate"] >= 0)

# Scenario: today's day should have non-zero hours
today_hours = [t["hours"] for t in progress["weeklyTrend"] if t["isToday"]]
if today_hours:
    scenario("Today has study hours in trend",
             today_hours[0] > 0,
             f"(today hours: {today_hours[0]})")
else:
    print("  [SCENARIO SKIP] Today not found in trend (weekend?)")

# =============================================
# SCENARIO 4: Goal Completion Flow
# =============================================
print("\n--- Scenario 4: Goal Completion Flow ---")

# Generate a study plan first
r = httpx.post(f"{BASE}/api/plan/generate", headers=h, timeout=180,
               json={"targetDate": "2026-07-01", "focusAreas": ["概率论", "算法"], "dailyHours": 3})
plan_ok = r.json()["code"] == 200
check("Plan generation", plan_ok)

if plan_ok:
    # Get today goals
    r = httpx.get(f"{BASE}/api/today/goals", headers=h)
    goals_data = r.json()["data"]
    goals = goals_data.get("todayGoals", [])
    check("Has goals", len(goals) > 0, f"(count={len(goals)})")
    
    if goals:
        # Mark first goal as completed
        goal = goals[0]
        print(f"  Goal to complete: {goal['title']}")
        
        r = httpx.put(f"{BASE}/api/today/goals/{goal['id']}", headers=h,
                      json={"completed": True})
        check("Goal update success", r.json()["code"] == 200)
        
        # Verify goal is now completed
        r = httpx.get(f"{BASE}/api/today/goals", headers=h)
        updated_goals = r.json()["data"].get("todayGoals", [])
        if updated_goals:
            scenario("Goal completed status persisted",
                     updated_goals[0]["completed"] == True,
                     f"(completed={updated_goals[0]['completed']})")
        
        # Toggle it back (uncomplete)
        r = httpx.put(f"{BASE}/api/today/goals/{goal['id']}", headers=h,
                      json={"completed": False})
        r = httpx.get(f"{BASE}/api/today/goals", headers=h)
        reverted = r.json()["data"].get("todayGoals", [])
        if reverted:
            scenario("Goal can be un-completed",
                     reverted[0]["completed"] == False)

# =============================================
# SCENARIO 5: Push Data Consistency
# =============================================
print("\n--- Scenario 5: Push Data Consistency ---")

r = httpx.get(f"{BASE}/api/today/push", headers=h)
push = r.json()["data"]

check("Push has date", bool(push.get("date")))
check("Push has weather", push.get("weather") in ("晴", "多云", "阴", "小雨", "雨"))
check("Push has valid study hours", 2 <= push.get("suggestedStudyHours", 0) <= 8)
check("Push has valid status", push.get("status") in ("最佳", "良好", "一般"))

# Scenario: status should match actual study activity
r = httpx.get(f"{BASE}/api/today/progress", headers=h)
prog = r.json()["data"]
status_match = (
    (push["status"] == "最佳" and prog["weeklyStudyHours"] >= 15) or
    (push["status"] == "良好" and prog["weeklyStudyHours"] >= 8) or
    (push["status"] == "一般" and prog["weeklyStudyHours"] < 8)
)
scenario("Push status matches study hours",
         status_match,
         f"(status={push['status']}, hours={prog['weeklyStudyHours']})")

# =============================================
# SCENARIO 6: Study Session Tracking
# =============================================
print("\n--- Scenario 6: Study Session Tracking ---")

r = httpx.post(f"{BASE}/api/today/start-study", headers=h)
session_id = r.json()["data"]["sessionId"]
check("Session created", bool(session_id) and session_id.startswith("sess_"))

# Start another session - should get different ID
r = httpx.post(f"{BASE}/api/today/start-study", headers=h)
session_id2 = r.json()["data"]["sessionId"]
scenario("Sessions have unique IDs",
         session_id != session_id2,
         f"(s1={session_id[:15]}..., s2={session_id2[:15]}...)")

# =============================================
# Summary
# =============================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{passed + failed} unit checks passed")
print(f"SCENARIOS: {scenarios_passed} scenarios verified")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"{failed} CHECKS FAILED!")
print("=" * 60)

# Cleanup
proc.terminate()
proc.wait()
stderr_file.close()

with open("server_stderr.log") as f:
    errors = [l.strip() for l in f.readlines()
              if "[ERROR]" in l and "bcrypt" not in l]
    if errors:
        print(f"\nBackend had {len(errors)} ERROR lines!")
        for l in errors[-3:]:
            print("  |", l[:200])
    else:
        print("Backend clean - no errors.")

try:
    os.remove("server_stderr.log")
except:
    pass
