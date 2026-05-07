# T3 FastAPI Example Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build YAML example cases in `examples/cases/` that exercise the committed FastAPI example service and match the user manual.

**Architecture:** This task only adds example case files and synchronizes documentation. The YAML files remain product examples for the future MwjRunner loader/engine; they do not add Python runtime code or dependencies.

**Tech Stack:** YAML example files, FastAPI example API documentation, existing Markdown docs, UV for verifying the example API tests.

---

## File Structure

- Create `examples/cases/health.yaml`: smoke health-check case for `GET /health`, covering `status_code` and `json_path`.
- Create `examples/cases/login.yaml`: login-only case for `POST /api/login`, covering variables, `status_code`, `json_path`, `body_contains`, and token extraction.
- Create `examples/cases/login_profile.yaml`: two-step auth flow that extracts token from login and reuses it in `GET /api/profile`.
- Create `examples/cases/health_fail.yaml`: intentionally failing assertion case for future failure-report demonstrations.
- Modify `doc/下一步计划.md`: mark T3 progress/completion and set T4 as next current task.
- Modify `doc/使用手册.md`: update stale implementation-status wording and ensure embedded YAML matches the files.
- Modify `doc/技术方案.md`: list the actual example case files in the recommended directory structure.
- Modify `doc/需求规格说明书.md`: adjust example-case wording to reflect that FastAPI example service and case files are now maintained artifacts.

## Task 1: Create health example case

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\examples\cases\health.yaml`

- [ ] **Step 1: Create the cases directory**

Run:

```bash
mkdir -p "E:/Y_pythonProject/MwjRunner/examples/cases"
```

Expected: directory exists and command exits 0.

- [ ] **Step 2: Write health.yaml**

Create `E:\Y_pythonProject\MwjRunner\examples\cases\health.yaml` with:

```yaml
name: 健康检查
tags: [smoke]
steps:
  - name: 服务健康状态
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: ok
```

- [ ] **Step 3: Verify YAML content can be parsed**

Run from repository root:

```bash
python - <<'PY'
from pathlib import Path
import yaml
path = Path('examples/cases/health.yaml')
data = yaml.safe_load(path.read_text(encoding='utf-8'))
assert data['name'] == '健康检查'
assert data['steps'][0]['request']['url'] == '/health'
print('health.yaml parsed')
PY
```

Expected output contains `health.yaml parsed`.

## Task 2: Create login and login-profile cases

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\examples\cases\login.yaml`
- Create: `E:\Y_pythonProject\MwjRunner\examples\cases\login_profile.yaml`

- [ ] **Step 1: Write login.yaml**

Create `E:\Y_pythonProject\MwjRunner\examples\cases\login.yaml` with:

```yaml
name: 登录成功
tags: [smoke, auth]
variables:
  username: demo
  password: "123456"
steps:
  - name: 使用正确账号登录
    request:
      method: POST
      url: /api/login
      headers:
        Content-Type: application/json
      json:
        username: ${username}
        password: ${password}
    extract:
      token: $.data.token
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.code
        expected: 0
      - type: json_path
        path: $.data.token
        expected: demo-token
      - type: body_contains
        expected: success
```

- [ ] **Step 2: Write login_profile.yaml**

Create `E:\Y_pythonProject\MwjRunner\examples\cases\login_profile.yaml` with:

```yaml
name: 登录后获取用户信息
tags: [smoke, auth]
variables:
  username: demo
  password: "123456"
steps:
  - name: 登录成功
    request:
      method: POST
      url: /api/login
      headers:
        Content-Type: application/json
      json:
        username: ${username}
        password: ${password}
    extract:
      token: $.data.token
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.code
        expected: 0
      - type: body_contains
        expected: success

  - name: 获取用户信息
    request:
      method: GET
      url: /api/profile
      headers:
        Authorization: Bearer ${token}
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.data.username
        expected: demo
      - type: body_contains
        expected: 示例用户
```

- [ ] **Step 3: Verify both YAML files can be parsed**

Run from repository root:

```bash
python - <<'PY'
from pathlib import Path
import yaml
for name in ['login.yaml', 'login_profile.yaml']:
    data = yaml.safe_load((Path('examples/cases') / name).read_text(encoding='utf-8'))
    assert data['steps']
    assert data['variables']['username'] == 'demo'
    print(f'{name} parsed')
PY
```

Expected output contains `login.yaml parsed` and `login_profile.yaml parsed`.

## Task 3: Create failure example case

**Files:**
- Create: `E:\Y_pythonProject\MwjRunner\examples\cases\health_fail.yaml`

- [ ] **Step 1: Write health_fail.yaml**

Create `E:\Y_pythonProject\MwjRunner\examples\cases\health_fail.yaml` with:

```yaml
name: 健康检查失败示例
tags: [demo, fail]
steps:
  - name: 故意写错健康状态
    request:
      method: GET
      url: /health
    assertions:
      - type: status_code
        expected: 200
      - type: json_path
        path: $.status
        expected: down
      - type: body_contains
        expected: service unavailable
```

- [ ] **Step 2: Verify failure case is intentionally mismatched with API**

Run from repository root:

```bash
python - <<'PY'
from pathlib import Path
import yaml
case = yaml.safe_load(Path('examples/cases/health_fail.yaml').read_text(encoding='utf-8'))
assert case['steps'][0]['assertions'][1]['expected'] == 'down'
assert case['steps'][0]['assertions'][2]['expected'] == 'service unavailable'
print('health_fail.yaml intentionally failing')
PY
```

Expected output contains `health_fail.yaml intentionally failing`.

## Task 4: Synchronize documentation

**Files:**
- Modify: `E:\Y_pythonProject\MwjRunner\doc\下一步计划.md`
- Modify: `E:\Y_pythonProject\MwjRunner\doc\使用手册.md`
- Modify: `E:\Y_pythonProject\MwjRunner\doc\技术方案.md`
- Modify: `E:\Y_pythonProject\MwjRunner\doc\需求规格说明书.md`

- [ ] **Step 1: Update next plan status**

In `doc/下一步计划.md`, change T3 to completed after files are written, add actual results, and move T4 into current task.

- [ ] **Step 2: Update user manual examples**

In `doc/使用手册.md`, remove stale statements that say `examples/api/` has not been created, and ensure YAML snippets match the four files in `examples/cases/`.

- [ ] **Step 3: Update technical and requirements docs**

In `doc/技术方案.md`, add `login.yaml` and `health_fail.yaml` under `examples/cases/`. In `doc/需求规格说明书.md`, keep example case requirements aligned with the actual files.

## Task 5: Review, verify, commit, and push

**Files:**
- Review all files created or modified in Tasks 1-4.

- [ ] **Step 1: Run FastAPI example tests**

Run:

```bash
cd "E:/Y_pythonProject/MwjRunner/examples/api" && uv run pytest
```

Expected output contains `9 passed`.

- [ ] **Step 2: Run YAML parse verification**

Run from repository root:

```bash
cd "E:/Y_pythonProject/MwjRunner" && python - <<'PY'
from pathlib import Path
import yaml
for path in sorted(Path('examples/cases').glob('*.yaml')):
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert data['name']
    assert data['steps']
    print(f'{path.as_posix()} parsed')
PY
```

Expected output lists all four YAML files and exits 0.

- [ ] **Step 3: Run project code-review skill**

Use the `code-review` skill against the current diff. Expected: no P0/P1 blockers.

- [ ] **Step 4: Commit exact files only**

Run:

```bash
git -C "E:/Y_pythonProject/MwjRunner" add -- "examples/cases/health.yaml" "examples/cases/login.yaml" "examples/cases/login_profile.yaml" "examples/cases/health_fail.yaml" "doc/下一步计划.md" "doc/使用手册.md" "doc/技术方案.md" "doc/需求规格说明书.md" "docs/superpowers/plans/2026-05-06-t3-fastapi-example-cases.md"
git -C "E:/Y_pythonProject/MwjRunner" commit -m "$(cat <<'EOF'
docs: add FastAPI-linked example cases

Provide YAML examples that exercise the committed FastAPI service so the upcoming loader, assertions, extraction, and variable reuse work has stable fixtures.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Expected: new commit is created.

- [ ] **Step 5: Verify again and push**

Run:

```bash
cd "E:/Y_pythonProject/MwjRunner/examples/api" && uv run pytest && git -C "E:/Y_pythonProject/MwjRunner" push
```

Expected: output contains `9 passed` and push succeeds.

## Self-Review

- Spec coverage: T3 requires health, login, token extraction/profile flow, and intentional failure examples. Tasks 1-3 cover all required examples; Task 4 keeps docs synchronized; Task 5 verifies and ships.
- Placeholder scan: no placeholder text remains in the plan.
- Type consistency: YAML fields use the documented case shape: `name`, `tags`, `variables`, `steps`, `request`, `extract`, `assertions`, `type`, `path`, `expected`.
