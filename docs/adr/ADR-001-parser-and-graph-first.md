# ADR-001: Parser and Graph First Intelligence

## Status

Accepted

## Context

Archon must reason about repositories at system scale. The project constitution
requires that repository understanding happens before LLM reasoning, and that
parsing, symbol resolution, and graph construction remain deterministic.

## Decision

Archon uses Tree-sitter for source parsing, a deterministic resolver pipeline for
symbol/reference resolution, PostgreSQL-backed graph records, and NetworkX for
initial graph traversal. Agents consume assembled context derived from graph,
impact, documentation, and keyword evidence.

## Consequences

- LLMs never parse code or resolve symbols.
- Repository graph generation can run without any model provider.
- Agent findings must cite context produced by repository intelligence.
- Resolver and graph improvements require benchmark validation.
