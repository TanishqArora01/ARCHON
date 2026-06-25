# agents.md

# Archon

## AI Staff Engineer Platform

Version: 1.0

Status: Project Constitution

---

# Mission

Build an AI Staff Engineer capable of understanding large-scale software systems, reasoning about architecture, predicting change impact, detecting architectural drift, identifying technical debt, and producing evidence-based engineering recommendations.

Archon is not an AI code review assistant.

Archon is a repository intelligence platform that enables AI systems to reason about software systems at repository scale.

---

# Product Vision

Most AI coding tools understand files.

Archon understands systems.

Traditional AI review tools answer:

> Is this code good?

Archon answers:

> Should this code exist?
>
> What architectural boundaries does it affect?
>
> What will break if it changes?
>
> Does it increase long-term complexity?
>
> Does it violate repository rules?
>
> Is there a better implementation already present elsewhere?

---

# Product Category

AI Staff Engineer Platform

---

# Product Positioning

Archon combines:

* Repository Intelligence
* Architecture Intelligence
* Impact Intelligence
* Technical Debt Intelligence
* Engineering Reasoning

into a single system.

---

# Core Principles

## Principle 1

Repository understanding comes before AI reasoning.

Bad:

Repository → LLM

Good:

Repository → Graph → Retrieval → Context → LLM

---

## Principle 2

Evidence before recommendations.

Every recommendation must include:

* Issue
* Evidence
* Reasoning
* Impact
* Recommendation

---

## Principle 3

High precision over high recall.

Do not maximize issue count.

Maximize trust.

A missed issue is acceptable.

False positives are expensive.

---

## Principle 4

Repository intelligence is the moat.

Models are replaceable.

Repository understanding is not.

---

## Principle 5

No hallucinated architecture.

All architectural claims must be backed by:

* Graph evidence
* Repository evidence
* Documentation evidence
* Rule evidence

---

# Deployment Strategy

## Phase 1

Open Source First

Self-hosted deployment.

Supported:

* Docker Compose
* Local PostgreSQL
* Local Redis
* Local Ollama
* Local Qdrant

---

## Phase 2

Cloud SaaS

Multi-tenant architecture.

Same intelligence layer.

Different deployment model.

---

# Model Strategy

Models are pluggable.

Supported providers:

* Ollama
* OpenAI
* Anthropic
* OpenRouter
* Azure OpenAI

Default OSS model:

Qwen via Ollama

The platform must never depend on a single model provider.

---

# Supported Languages

## Phase 1

* Python
* JavaScript
* TypeScript

## Future

* Java
* Go
* Rust
* C#

Language support is parser-driven.

The architecture must remain language-agnostic.

---

# Repository Intelligence Architecture

Repository

→ Snapshot

→ Analysis Run

→ Parsing

→ Symbol Extraction

→ Symbol Resolution

→ Graph Construction

→ Impact Analysis

→ Retrieval

→ Reasoning

---

# Repository Hierarchy

Repository

→ Domain

→ Module

→ File

→ Class

→ Function

---

# Knowledge Graph

## Node Types

Repository

Module

File

Class

Function

Method

API

Database

External Dependency

Document

---

## Edge Types

CALLS

IMPORTS

DEPENDS_ON

USES

IMPLEMENTS

INHERITS

EXPOSES

REFERENCES

DEFINED_IN

BELONGS_TO

---

# Resolver Philosophy

Resolver accuracy is critical.

Graph quality determines recommendation quality.

Resolver stages:

1. Alias Resolution
2. Relative Import Resolution
3. Package Resolution
4. Export Resolution
5. Re-export Resolution
6. Symbol Resolution

Unresolved references must never be discarded.

---

# Resolver Failure Categories

UNRESOLVED_ALIAS

UNRESOLVED_EXPORT

UNRESOLVED_PACKAGE

UNRESOLVED_RELATIVE_IMPORT

UNRESOLVED_DYNAMIC_IMPORT

UNRESOLVED_STAR_IMPORT

UNKNOWN

---

# Architecture Rules

Rules are repository-defined.

Location:

.aegis/rules.yaml

Example:

Controller:
can_call:
- Service

Service:
can_call:
- Repository

Forbidden:

Controller:
cannot_call:
- Database

Architecture intelligence must use repository rules as the source of truth.

---

# Repository Memory

Repository memory stores:

README

ADR

RFC

Design Documents

Runbooks

API Specifications

Architecture Documentation

Repository memory is documentation intelligence.

Repository memory is not source code storage.

---

# Retrieval Philosophy

Retrieval must be hybrid.

Context =

Graph Retrieval

*

Documentation Retrieval

*

Keyword Retrieval

---

# Agent Philosophy

Agents are introduced only after:

* Repository Graph
* Repository Memory
* Hybrid Retrieval

are validated.

Agents are reasoning systems.

Agents are not retrieval systems.

---

# Agent Hierarchy

## Planner Agent

Receives:

* User Request
* PR
* Repository Context

Decides:

Which specialists should execute.

---

## Architecture Agent

Responsibilities:

* Layer Violations
* Boundary Violations
* Architecture Drift
* Dependency Health

---

## Impact Agent

Responsibilities:

* Change Impact
* Dependency Analysis
* Blast Radius Estimation
* Risk Scoring

---

## Security Agent

Responsibilities:

* Security Risks
* Authentication Issues
* Secret Exposure
* Dangerous Patterns

---

## Maintainability Agent

Responsibilities:

* Complexity
* Duplication
* Technical Debt
* Refactoring Opportunities

---

## Testing Agent

Responsibilities:

* Missing Tests
* Weak Coverage
* Edge Cases
* Regression Risk

---

## Fix Agent

Responsibilities:

* Generate Fix Suggestions
* Generate Patch Candidates
* Explain Tradeoffs

The Fix Agent never modifies repositories directly.

---

## Synthesis Agent

Produces:

* Final Findings
* Evidence
* Reasoning
* Risk
* Recommendations

---

# Review Output Standard

Every finding must follow:

Issue

Evidence

Reasoning

Impact

Recommendation

Bad:

Rename variable.

Good:

Authentication logic duplicates AuthService.

Excellent:

This change introduces a second authentication path.

AuthService currently acts as the repository's single source of truth.

Maintaining parallel authentication flows increases authorization inconsistency risk and future maintenance cost.

---

# Success Metrics

## Repository Intelligence

Symbol Extraction Accuracy > 90%

Reference Resolution > 70% minimum

Target > 85%

---

## Impact Intelligence

Impact Precision > 80%

Impact Recall > 75%

---

## Architecture Intelligence

Boundary Violation Precision > 85%

---

## Recommendation Quality

False Positive Rate < 10%

---

# Non-Goals

Archon is not:

* A chatbot
* A code generator
* A landing-page project
* A wrapper around an LLM
* A PR comment spam tool

Archon is a repository intelligence and engineering reasoning platform.

---

# Long-Term Vision

Archon becomes the AI Staff Engineer for software organizations.

Not merely a code reviewer.

A system that understands:

* Code
* Architecture
* Documentation
* Dependencies
* Evolution
* Technical Debt

and helps engineering teams make better long-term decisions.

# Technical Execution Architecture

This section defines the implementation-level architecture of Archon.

All contributors and AI agents must follow these standards unless an ADR (Architecture Decision Record) explicitly supersedes them.

---

## Primary Language

Backend Language:

- Python 3.13+

Rationale:

- Mature AST ecosystem
- Strong AI tooling ecosystem
- Excellent Tree-sitter integration
- Strong graph and data tooling
- Fast development velocity

---

## Core Backend Framework

API Layer:

- FastAPI

Requirements:

- Fully async architecture
- Dependency injection
- OpenAPI-first development
- Pydantic v2 validation

---

## Data Storage

Primary Database:

- PostgreSQL

Responsibilities:

- Repository metadata
- Snapshots
- Analysis runs
- Symbols
- References
- Dependency edges
- Metrics

---

## Cache and Coordination

Technology:

- Redis

Responsibilities:

- OAuth state
- Refresh token revocation
- Webhook idempotency
- Background task coordination
- Rate limiting

Redis must never be treated as the source of truth.

---

## Code Parsing Layer

Primary Parser:

- Tree-sitter

Purpose:

- Language-independent parsing
- AST generation
- Symbol extraction
- Dependency discovery

Supported Languages:

Phase 1:
- Python
- JavaScript
- TypeScript

Future:
- Java
- Go
- Rust
- C#

---

## Tree-sitter Query Strategy

Language support must use:

- Tree-sitter grammar
- Tree-sitter query files
- Language-specific extractors

Avoid regex-based parsing.

Avoid LLM-based parsing.

AST extraction must remain deterministic.

---

## Symbol Resolution Layer

Archon uses a dedicated resolver pipeline.

Stages:

1. Alias Resolution
2. Relative Import Resolution
3. Package Resolution
4. Export Resolution
5. Re-export Resolution
6. Symbol Resolution

Resolution logic must be deterministic.

LLMs must never participate in symbol resolution.

---

## Knowledge Graph Layer

Graph Storage:

Current:
- PostgreSQL

Graph Traversal:
- NetworkX

Future:
- Neo4j

Graph is the primary intelligence layer.

The graph must be buildable without any LLM.

---

## Repository Memory Layer

Documentation Store:

- Qdrant

Indexed Documents:

- README
- ADR
- RFC
- Architecture Docs
- API Specifications
- Runbooks

Repository memory is separate from source-code intelligence.

---

## Embedding Strategy

Default Embedding Provider:

- BGE
- Nomic
- Qwen Embeddings

Embeddings must be provider-agnostic.

All embedding providers must implement the same interface.

---

## Model Runtime

Default Runtime:

- Ollama

Default Model:

- Qwen

Requirements:

- Local execution supported
- Provider abstraction required

The platform must never be tightly coupled to a specific model.

---

## Agent Communication

Agents communicate through structured messages.

Format:

JSON

Example:

{
  "repository_id": "...",
  "analysis_run_id": "...",
  "context": {...},
  "task": "...",
  "constraints": [...]
}

Agents must never exchange free-form text as their primary interface.

---

## Agent Orchestration

Architecture:

Planner
↓
Specialists
↓
Synthesis

Execution:

Async

Preferred Runtime:

- LangGraph (future)
- Custom orchestration layer (initial)

Agent execution must be deterministic where possible.

---

## Context Assembly Pipeline

Context Builder

=
Graph Context
+
Impact Context
+
Repository Memory
+
Keyword Matches

Only assembled context may be sent to LLMs.

Raw repositories must never be sent directly.

---

## Review Generation Pipeline

Repository
↓
Graph
↓
Impact Analysis
↓
Context Assembly
↓
Agent Analysis
↓
Synthesis
↓
Review Output

LLMs never bypass the graph layer.

---

## Observability

Required:

- OpenTelemetry

Metrics:

- Parse duration
- Resolver accuracy
- Graph size
- Retrieval latency
- Agent latency
- Review accuracy

All major components must expose metrics.

---

## Testing Standards

Required:

- pytest
- mypy
- ruff

Every new intelligence layer must include:

- Unit tests
- Fixture repository tests
- Real repository benchmark tests

No feature is complete without benchmark validation.

---

## Architecture Decision Records

Major technical decisions must be documented.

Location:

docs/adr/

Examples:

ADR-001-parser-selection.md

ADR-002-graph-storage.md

ADR-003-agent-orchestration.md

Architectural decisions must not live only in code.

# Architectural Invariants

1. Repository intelligence must function without an LLM.

2. Symbol resolution must remain deterministic.

3. Knowledge graph generation must remain reproducible.

4. Repository memory must be independent of source code parsing.

5. Agents consume context; agents do not retrieve context.

6. Recommendations require evidence.

7. No direct repository → LLM workflow is allowed.

8. Every intelligence layer must be benchmarked on real repositories.

9. Models are replaceable.

10. Repository understanding is the primary moat.

# Engineering Standards

## Code Quality

Required:

- Ruff
- MyPy
- Pytest

Every pull request must pass:

ruff check

mypy

pytest

before merge.

---

## Type Safety

All public interfaces must use:

- Pydantic models
- Explicit typing

Avoid:

Any

except when unavoidable.

---

## API Standards

Requirements:

- OpenAPI-first
- Versioned endpoints
- Consistent response models
- Structured error handling

Example:

/api/v1/...

---

## Database Standards

Requirements:

- Alembic migrations
- Async SQLAlchemy
- Repository pattern where appropriate

Direct SQL should be minimized.

---

## Logging

Use structured logging.

Never log:

- secrets
- access tokens
- credentials

All logs must support machine analysis.

# Benchmark Philosophy

Repository intelligence must be validated on real repositories.

Synthetic examples are insufficient.

Current benchmark repositories:

- FastAPI
- Requests
- Typer

Future benchmark repositories:

- Django
- Flask
- LangChain
- Home Assistant
- Kubernetes
- Go standard libraries

Every intelligence improvement must be benchmarked.

Benchmarks are first-class product features.

# Intelligence Maturity Model

Phase 1

Repository Ingestion

Phase 2

Parsing

Phase 3

Knowledge Graph

Phase 4

Impact Analysis

Phase 4.5

Benchmark Validation

Phase 4.6

Resolver Intelligence

Phase 5

Repository Memory

Phase 6

Hybrid Retrieval

Phase 7

Context Assembly

Phase 8

Engineering Recommendations

Phase 9

Agentic Intelligence

Phase 10

Architecture Drift Detection

Phase 11

Technical Debt Forecasting

Phase 12

AI Staff Engineer

# Anti-Patterns

Never do:

Repository
→ LLM
→ Review

Never do:

Code
→ Embedding
→ Recommendation

Never do:

LLM-based parsing

Never do:

LLM-based symbol resolution

Never do:

Agent retrieval without graph context

Never do:

Recommendations without evidence

Never do:

Architecture conclusions without repository rules

Never optimize for issue count.

Optimize for trust.

Structure: agents.md
│
├── Mission
├── Product Vision
├── Product Category
├── Product Positioning
├── Core Principles
├── Deployment Strategy
├── Model Strategy
├── Technical Execution Architecture   ← NEW
├── Supported Languages
├── Repository Intelligence Architecture
├── Repository Hierarchy
├── Knowledge Graph
├── Resolver Philosophy
├── Resolver Failure Categories
├── Architecture Rules
├── Repository Memory
├── Retrieval Philosophy
├── Agent Philosophy
├── Agent Hierarchy
├── Review Output Standard
├── Success Metrics
├── Architectural Invariants          ← NEW
├── Non-Goals
└── Long-Term Vision