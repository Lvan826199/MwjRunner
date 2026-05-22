"""CI 配置模板生成器。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_current_user
from app.core.database import get_db
from app.core.permissions import check_resource_access
from app.models.pipeline import Pipeline
from app.models.user import User

router = APIRouter(prefix="/api/ci-templates", tags=["CI 模板生成"])


@router.get("/{pipeline_id}")
async def generate_ci_config(
    pipeline_id: int,
    platform: str = Query(None, description="覆盖平台: github, gitlab, jenkins"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """根据 Pipeline 配置生成 CI 配置文件内容。"""
    p = await check_resource_access(db, Pipeline, pipeline_id, user)
    target_platform = platform or p.platform or "github"

    generators = {
        "github": _generate_github_actions,
        "gitlab": _generate_gitlab_ci,
        "jenkins": _generate_jenkinsfile,
    }

    generator = generators.get(target_platform)
    if not generator:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {target_platform}")

    content = generator(p)
    return {
        "platform": target_platform,
        "filename": _get_filename(target_platform),
        "content": content,
    }


@router.get("")
async def list_templates(_user: User = Depends(get_current_user)):
    """获取支持的 CI 平台列表。"""
    return {
        "platforms": [
            {"id": "github", "name": "GitHub Actions", "filename": ".github/workflows/mwjrunner.yml"},
            {"id": "gitlab", "name": "GitLab CI", "filename": ".gitlab-ci.yml"},
            {"id": "jenkins", "name": "Jenkins", "filename": "Jenkinsfile"},
        ]
    }


def _get_filename(platform: str) -> str:
    return {
        "github": ".github/workflows/mwjrunner.yml",
        "gitlab": ".gitlab-ci.yml",
        "jenkins": "Jenkinsfile",
    }.get(platform, "ci-config.yml")


def _generate_github_actions(p: Pipeline) -> str:
    trigger_section = ""
    if p.trigger_type == "schedule" and p.cron_expr:
        trigger_section = f"""  schedule:
    - cron: '{p.cron_expr}'"""
    elif p.trigger_type == "webhook":
        trigger_section = """  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]"""
    else:
        trigger_section = "  workflow_dispatch:"

    env_vars = ""
    if p.base_url:
        env_vars = f"""
env:
  BASE_URL: {p.base_url}
  ENV_NAME: {p.env_name or "test"}"""

    tags_filter = ""
    if p.case_filter_tags:
        tags_filter = f" --tags {p.case_filter_tags}"

    notify_step = ""
    if p.notify_on_fail and p.notify_webhook:
        notify_step = f"""
      - name: 通知失败
        if: failure()
        run: |
          curl -X POST '{p.notify_webhook}' \\
            -H 'Content-Type: application/json' \\
            -d '{{"msgtype":"text","text":{{"content":"[MwjRunner] Pipeline {p.name} 执行失败 - ${{{{github.sha}}}}"}}}}'"""  # noqa: E501

    return f"""name: MwjRunner - {p.name}

on:
{trigger_section}
{env_vars}
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install MwjRunner
        run: pip install mwjrunner

      - name: Run Tests
        run: |
          mwjrunner run . \\
            --base-url ${{{{ env.BASE_URL }}}} \\
            --env ${{{{ env.ENV_NAME }}}} \\
            --report json,html \\
            --report-dir reports{tags_filter}

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-report
          path: reports/
{notify_step}
"""


def _generate_gitlab_ci(p: Pipeline) -> str:
    schedule_section = ""
    if p.trigger_type == "schedule" and p.cron_expr:
        schedule_section = """
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
"""

    tags_filter = ""
    if p.case_filter_tags:
        tags_filter = f" --tags {p.case_filter_tags}"

    base_url = p.base_url or "http://localhost:8080"
    env_name = p.env_name or "test"

    notify_section = ""
    if p.notify_on_fail and p.notify_webhook:
        notify_section = f"""
  after_script:
    - |
      if [ "$CI_JOB_STATUS" == "failed" ]; then
        curl -X POST '{p.notify_webhook}' \\
          -H 'Content-Type: application/json' \\
          -d '{{"msgtype":"text","text":{{"content":"[MwjRunner] Pipeline {p.name} 失败 - $CI_COMMIT_SHA"}}}}'
      fi"""

    return f"""stages:
  - test

mwjrunner-test:
  stage: test
  image: python:3.11-slim
  variables:
    BASE_URL: "{base_url}"
    ENV_NAME: "{env_name}"
{schedule_section}
  before_script:
    - pip install mwjrunner

  script:
    - |
      mwjrunner run . \\
        --base-url $BASE_URL \\
        --env $ENV_NAME \\
        --report json,html \\
        --report-dir reports{tags_filter}

  artifacts:
    when: always
    paths:
      - reports/
    expire_in: 7 days
{notify_section}
"""


def _generate_jenkinsfile(p: Pipeline) -> str:
    trigger_section = ""
    if p.trigger_type == "schedule" and p.cron_expr:
        trigger_section = f"""    triggers {{
        cron('{p.cron_expr}')
    }}"""

    tags_filter = ""
    if p.case_filter_tags:
        tags_filter = f" --tags {p.case_filter_tags}"

    base_url = p.base_url or "http://localhost:8080"
    env_name = p.env_name or "test"

    notify_section = ""
    if p.notify_on_fail and p.notify_webhook:
        notify_section = f"""
        failure {{
            sh '''
                curl -X POST '{p.notify_webhook}' \\
                  -H 'Content-Type: application/json' \\
                  -d '{{"msgtype":"text","text":{{"content":"[MwjRunner] Pipeline {p.name} 失败"}}}}'
            '''
        }}"""

    return f"""pipeline {{
    agent any
{trigger_section}
    environment {{
        BASE_URL = '{base_url}'
        ENV_NAME = '{env_name}'
    }}

    stages {{
        stage('Install') {{
            steps {{
                sh 'pip install mwjrunner'
            }}
        }}

        stage('Test') {{
            steps {{
                sh '''
                    mwjrunner run . \\
                      --base-url $BASE_URL \\
                      --env $ENV_NAME \\
                      --report json,html \\
                      --report-dir reports{tags_filter}
                '''
            }}
        }}
    }}

    post {{
        always {{
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            publishHTML(target: [
                reportDir: 'reports',
                reportFiles: '*/report.html',
                reportName: 'MwjRunner Report'
            ])
        }}{notify_section}
    }}
}}
"""
