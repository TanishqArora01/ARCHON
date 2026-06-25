"""Shared repository analysis pipeline used by the worker and API."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from src.agents.llm_provider import build_llm_provider
from src.agents.schemas import Severity
from src.agents.workflow import build_archon_graph
from src.core.config import settings
from src.db.models import AnalysisJob, AnalysisRun, ReviewReport
from src.db.session import AsyncSessionLocal
from src.environment.ingestion import RepositoryIngestor
from src.environment.parser.engine import ParserEngine
from src.environment.resolver.pipeline import SymbolResolverPipeline
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.providers import build_embedding_provider
from src.memory.vector_store import QdrantMemoryStore
from src.remediation.engine import AutonomousRemediationEngine
from src.retrieval.engine import HybridRetrievalEngine
from src.retrieval.schemas import AssembledAgentContext, SemanticContext, StructuralContext
from src.vcs.checkout import GitRepositoryCheckout, RepositoryCheckoutError
from src.vcs.git_analyzer import GitDiffAnalyzer
from src.vcs.publisher import build_vcs_publisher

logger = logging.getLogger(__name__)


class ZeroEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]


class FallbackEmbeddingProvider(BaseEmbeddingProvider):
    """Use the primary embedding provider, falling back to zero vectors on failure."""

    def __init__(self, primary: BaseEmbeddingProvider, dimensions: int = 768):
        self.primary = primary
        self.dimensions = dimensions

    async def embed_query(self, text: str) -> list[float]:
        try:
            return await self.primary.embed_query(text)
        except Exception as exc:
            logger.warning("Embedding provider unavailable, using zero vector: %s", exc)
            return [0.0] * self.dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return await self.primary.embed_documents(texts)
        except Exception as exc:
            logger.warning("Embedding provider unavailable, using zero vectors: %s", exc)
            return [[0.0] * self.dimensions for _ in texts]


def _build_embedding_provider() -> BaseEmbeddingProvider:
    try:
        return FallbackEmbeddingProvider(build_embedding_provider())
    except Exception as exc:
        logger.warning("Could not build embedding provider, using zero vectors: %s", exc)
        return ZeroEmbeddingProvider()


async def _mark_job(job_id: str | None, status: str, error: str | None = None) -> None:
    if not job_id:
        return
    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, job_id)
        if not job:
            return
        job.status = status
        job.last_error = error
        if status == "running":
            job.attempts += 1
        await session.commit()


async def _link_job_to_analysis_run(job_id: str | None, snapshot_id: str) -> str | None:
    if not job_id:
        return None
    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, job_id)
        if not job:
            return None
        result = await session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.snapshot_id == snapshot_id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()
        if run:
            job.analysis_run_id = run.id
        await session.commit()
        return run.id if run else None


async def _get_repository_checkout_credentials(repository_id: str | None) -> tuple[str | None, str | None]:
    from src.core.secrets import SecretManager
    from src.db.models import Repository, VCSInstallation

    if not repository_id:
        return None, None
    async with AsyncSessionLocal() as session:
        repository = await session.get(Repository, repository_id)
        if not repository or not repository.installation_id:
            return None, repository.provider if repository else None
        installation = await session.get(VCSInstallation, repository.installation_id)
        if not installation or not installation.access_token_ciphertext:
            return None, repository.provider
        try:
            return SecretManager().decrypt(installation.access_token_ciphertext), repository.provider
        except ValueError:
            logger.warning("Repository credentials are not decryptable for repository_id=%s", repository_id)
            return None, repository.provider


async def _save_review_report(analysis_run_id: str | None, tracking_token: str, report_payload: dict) -> None:
    if not analysis_run_id:
        return
    async with AsyncSessionLocal() as session:
        session.add(
            ReviewReport(
                id=str(uuid.uuid4()),
                analysis_run_id=analysis_run_id,
                tracking_token=tracking_token,
                report=report_payload,
            )
        )
        await session.commit()


async def process_repository_analysis_task(
    repo_path_or_url: str,
    commit_sha: str,
    diff_text: str,
    event_metadata: dict[str, Any],
) -> None:
    logger.info("Processing task for repo=%s commit=%s", repo_path_or_url, commit_sha)

    publisher = build_vcs_publisher()
    job_id = event_metadata.get("job_id")
    repository_id = event_metadata.get("repository_id")
    access_token, provider = await _get_repository_checkout_credentials(repository_id)
    checkout = GitRepositoryCheckout(settings.WORKTREE_CACHE_DIR)
    try:
        await _mark_job(job_id, "running")
        local_path = await checkout.prepare(repo_path_or_url, commit_sha, access_token=access_token, provider=provider)
    except RepositoryCheckoutError as exc:
        message = f"Analysis failed before ingestion: repository checkout failed: {exc}"
        await publisher.publish_analysis_report(repo_path_or_url, commit_sha, message)
        await _mark_job(job_id, "failed", str(exc))
        logger.error("Repository checkout failed for repo=%s commit=%s", repo_path_or_url, commit_sha)
        return

    ingestor = RepositoryIngestor()
    try:
        snapshot_id = await ingestor.ingest(local_path, repository_id)
        analysis_run_id = await _link_job_to_analysis_run(job_id, snapshot_id)
    except Exception as exc:
        message = f"Analysis failed during deterministic repository ingestion: {exc}"
        await publisher.publish_analysis_report(repo_path_or_url, commit_sha, message)
        await _mark_job(job_id, "failed", str(exc))
        logger.exception("Repository ingestion failed for repo=%s", repo_path_or_url)
        return

    async with AsyncSessionLocal() as session:
        try:
            resolver = SymbolResolverPipeline()
            await resolver.execute_pipeline(snapshot_id, session)
        except Exception as exc:
            logger.warning("SymbolResolver error: %s", exc)

        analyzer = GitDiffAnalyzer()
        try:
            impacted_symbols = await analyzer.map_diff_to_symbols(session, snapshot_id, diff_text)
            target_symbol_id = impacted_symbols[0] if impacted_symbols else "unknown"
        except Exception as exc:
            logger.warning("GitDiffAnalyzer error: %s", exc)
            target_symbol_id = "unknown"

        try:
            from qdrant_client import AsyncQdrantClient

            qdrant_store = QdrantMemoryStore(client=AsyncQdrantClient(url=settings.QDRANT_URL))
            embedding_provider = _build_embedding_provider()
            retrieval_engine = HybridRetrievalEngine(provider=embedding_provider)
            context = await retrieval_engine.execute_fused_retrieval(
                db_session=session,
                qdrant_store=qdrant_store,
                snapshot_id=snapshot_id,
                collection_name="archon_docs",
                target_symbol_id=target_symbol_id,
                query_text=f"Analyze changes for {commit_sha}",
            )
        except Exception as exc:
            logger.warning("Retrieval error: %s", exc)
            context = AssembledAgentContext(
                tracking_token=f"run-{snapshot_id[:8]}",
                structural=StructuralContext(
                    impacted_file_paths=[],
                    impacted_symbol_ids=[],
                    blast_radius_score=0.0,
                ),
                semantic=SemanticContext(documentation_chunks=[], relevance_scores=[], source_files=[]),
            )

    report_markdown, final_report, tracking_token = await _run_agent_workflow(context)

    remediation_diffs: list[str] = []
    if final_report and final_report.findings:
        high_findings = [finding for finding in final_report.findings if finding.severity == Severity.HIGH]
        if high_findings:
            try:
                remediation_engine = AutonomousRemediationEngine(llm_provider=build_llm_provider())
                parser_engine = ParserEngine()
                for finding in high_findings:
                    diff = await remediation_engine.generate_verifiable_fix(
                        parser_engine=parser_engine,
                        finding=finding,
                        original_context=finding.evidence,
                        target_symbol_id=target_symbol_id,
                        language="python",
                    )
                    if diff:
                        remediation_diffs.append(diff)
            except Exception as exc:
                logger.warning("Remediation engine error: %s", exc)

    if remediation_diffs:
        report_markdown += "\n\n## Verified Remediation Patches\n\n"
        for index, diff in enumerate(remediation_diffs, 1):
            report_markdown += f"### Patch {index}\n```diff\n{diff}\n```\n\n"

    if final_report:
        await _save_review_report(
            analysis_run_id,
            tracking_token,
            {
                "findings": [finding.model_dump() for finding in final_report.findings],
                "agent_name": final_report.agent_name,
                "routing_rationale": event_metadata.get("routing_rationale", ""),
            },
        )

    await publisher.publish_analysis_report(repo_path_or_url, commit_sha, report_markdown)
    await _mark_job(job_id, "completed")
    logger.info("Task processing completed for snapshot=%s", snapshot_id)


async def _run_agent_workflow(context: AssembledAgentContext) -> tuple[str, Any, str]:
    try:
        graph = build_archon_graph()
        state = {
            "assembled_context": context,
            "selected_agents": [],
            "raw_specialist_reports": [],
            "routing_rationale": "",
            "final_report": None,
        }
        result_state = await graph.ainvoke(state)
        final_report = result_state.get("final_report")
        routing_rationale = result_state.get("routing_rationale", "")
        if final_report:
            report_markdown = final_report.model_dump_json(indent=2)
            if routing_rationale:
                report_markdown = f"<!-- Routing: {routing_rationale} -->\n{report_markdown}"
            return report_markdown, final_report, final_report.tracking_token
        return "No issues found.", None, context.tracking_token
    except Exception as exc:
        logger.warning("Agent workflow error: %s", exc)
        return "Error occurred during analysis.", None, context.tracking_token
