# ADR-002: Repository Architecture Rules as Source of Truth

## Status

Accepted

## Context

Archon must not hallucinate architecture. Architectural claims must be backed by
repository rules, graph evidence, repository evidence, or documentation evidence.
The constitution defines `.aegis/rules.yaml` as the location for repository-owned
architecture rules.

## Decision

Archon loads `.aegis/rules.yaml` during hybrid retrieval when a snapshot has a
repository path. The drift engine evaluates graph edges against those rules and
adds violations to the assembled structural context before any agent executes.

## Consequences

- The Architecture Agent receives rule evidence as context instead of discovering
  rules itself.
- Missing rules produce no architecture-rule claims.
- Rule parsing and drift detection remain deterministic and testable.
