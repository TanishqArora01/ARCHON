from __future__ import annotations

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select

from src.api.auth import CurrentUser
from src.api.schemas import JobRead, ProviderRepositoryImport, ProviderRepositoryRead, RepositoryCreate, RepositoryRead
from src.api.security import require_api_token
from src.core.config import settings
from src.core.secrets import SecretManager
from src.db.models import AnalysisJob, Repository, VCSInstallation
from src.db.session import AsyncSessionLocal
from src.services.analysis_jobs import enqueue_repository_analysis, run_inline_analysis
from src.services.repositories import get_or_create_default_tenant, upsert_repository

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"], dependencies=[Depends(require_api_token)])


def _read_repository(repo: Repository) -> RepositoryRead:
    return RepositoryRead(
        id=repo.id,
        provider=repo.provider,
        owner=repo.owner,
        name=repo.name,
        clone_url=repo.clone_url,
        default_branch=repo.default_branch,
    )


@router.post("", response_model=RepositoryRead)
async def create_repository(payload: RepositoryCreate, background_tasks: BackgroundTasks) -> RepositoryRead:
    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_default_tenant(session)
        repo = await upsert_repository(
            session,
            provider=payload.provider,
            owner=payload.owner,
            name=payload.name,
            clone_url=payload.clone_url,
            default_branch=payload.default_branch,
            tenant_id=tenant.id,
        )

        _, task_payload, queued = await enqueue_repository_analysis(session, repo, tenant_id=tenant.id, event_type="connect")
        await session.commit()

    if not queued:
        background_tasks.add_task(run_inline_analysis, task_payload)

    return _read_repository(repo)



@router.get("", response_model=list[RepositoryRead])
async def list_repositories() -> list[RepositoryRead]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))
        return [_read_repository(repo) for repo in result.scalars().all()]


@router.get("/provider/{provider}", response_model=list[ProviderRepositoryRead])
async def list_provider_repositories(
    provider: str,
    user: CurrentUser,
) -> list[ProviderRepositoryRead]:
    installation = await _get_user_installation(user, provider)
    token = _decrypt_installation_token(installation)
    return await _fetch_provider_repositories(provider, token)


@router.post("/provider/import", response_model=RepositoryRead)
async def import_provider_repository(
    payload: ProviderRepositoryImport,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> RepositoryRead:
    installation = await _get_user_installation(user, payload.provider)
    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_default_tenant(session)
        repo = await upsert_repository(
            session,
            provider=payload.provider,
            owner=payload.owner,
            name=payload.name,
            clone_url=payload.clone_url,
            default_branch=payload.default_branch,
            tenant_id=tenant.id,
            installation_id=installation.id,
        )

        _, task_payload, queued = await enqueue_repository_analysis(session, repo, tenant_id=tenant.id, event_type="import")
        await session.commit()

    if not queued:
        background_tasks.add_task(run_inline_analysis, task_payload)

    return _read_repository(repo)


@router.post("/{repository_id}/analyze", response_model=JobRead)
async def trigger_repository_analysis(repository_id: str, background_tasks: BackgroundTasks) -> JobRead:
    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        tenant = await get_or_create_default_tenant(session)
        job_id, task_payload, queued = await enqueue_repository_analysis(
            session,
            repo,
            tenant_id=tenant.id,
            event_type="manual",
        )
        await session.commit()
        job = await session.get(AnalysisJob, job_id)

    if not queued:
        background_tasks.add_task(run_inline_analysis, task_payload)

    if not job:
        raise HTTPException(status_code=500, detail="Failed to create analysis job")

    return JobRead(
        id=job.id,
        status=job.status,
        repository_id=job.repository_id,
        analysis_run_id=job.analysis_run_id,
        attempts=job.attempts,
        last_error=job.last_error,
        payload=job.payload,
    )


@router.get("/{repository_id}", response_model=RepositoryRead)
async def get_repository(repository_id: str) -> RepositoryRead:
    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        return _read_repository(repo)


async def _get_user_installation(user: dict, provider: str) -> VCSInstallation:
    if provider not in {"github", "gitlab"}:
        raise HTTPException(status_code=404, detail="Unsupported repository provider")

    installation_id = user.get("sub")
    if not installation_id:
        raise HTTPException(status_code=401, detail="Missing VCS installation")

    async with AsyncSessionLocal() as session:
        installation = await session.get(VCSInstallation, installation_id)
        if not installation or installation.provider != provider:
            raise HTTPException(status_code=403, detail=f"No connected {provider} account")
        return installation


def _decrypt_installation_token(installation: VCSInstallation) -> str:
    try:
        token = SecretManager().decrypt(installation.access_token_ciphertext)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="VCS credentials are not decryptable") from exc
    if not token:
        raise HTTPException(status_code=403, detail="Connected provider has no access token")
    return token


async def _fetch_provider_repositories(provider: str, access_token: str) -> list[ProviderRepositoryRead]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        if provider == "github":
            response = await client.get(
                f"{settings.GITHUB_API_URL.rstrip('/')}/user/repos",
                params={"per_page": 100, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            return [
                ProviderRepositoryRead(
                    provider="github",
                    owner=item["owner"]["login"],
                    name=item["name"],
                    clone_url=item["clone_url"],
                    default_branch=item.get("default_branch"),
                    private=bool(item.get("private", False)),
                )
                for item in response.json()
            ]

        if provider == "gitlab":
            response = await client.get(
                f"{settings.GITLAB_API_URL.rstrip('/')}/api/v4/projects",
                params={"membership": "true", "simple": "true", "per_page": 100, "order_by": "last_activity_at"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            repos: list[ProviderRepositoryRead] = []
            for item in response.json():
                namespace = item.get("namespace") or {}
                repos.append(
                    ProviderRepositoryRead(
                        provider="gitlab",
                        owner=namespace.get("full_path") or item.get("path_with_namespace", "").split("/")[0],
                        name=item["path"],
                        clone_url=item["http_url_to_repo"],
                        default_branch=item.get("default_branch"),
                        private=item.get("visibility") == "private",
                    )
                )
            return repos

    raise HTTPException(status_code=404, detail="Unsupported repository provider")
