from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Repository, Tenant


async def get_or_create_default_tenant(session: AsyncSession) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.slug == "default"))
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant

    tenant = Tenant(name="Default", slug="default")
    session.add(tenant)
    await session.flush()
    return tenant


async def upsert_repository(
    session: AsyncSession,
    provider: str,
    owner: str,
    name: str,
    clone_url: str,
    tenant_id: str,
    default_branch: str | None = None,
    installation_id: str | None = None,
) -> Repository:
    result = await session.execute(
        select(Repository).where(
            Repository.tenant_id == tenant_id,
            Repository.provider == provider,
            Repository.owner == owner,
            Repository.name == name,
        )
    )
    repository = result.scalar_one_or_none()
    if repository is None:
        repository = Repository(
            tenant_id=tenant_id,
            provider=provider,
            owner=owner,
            name=name,
            clone_url=clone_url,
            default_branch=default_branch,
            installation_id=installation_id,
        )
        session.add(repository)
    else:
        repository.clone_url = clone_url
        repository.default_branch = default_branch or repository.default_branch
        repository.installation_id = installation_id or repository.installation_id
    await session.flush()
    return repository
