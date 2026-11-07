---
doc_id: fusion-finance/changelog
product: fusion-finance
class: app
entry: service
doc_type: changelog
title: { zh: "fusion-finance 变更日志", en: "fusion-finance changelog" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - README.md
---

# Changelog

## Unreleased

- docs: adopt fusion docs-system v1.1 contract (app x service) — added docs/product-page.md, docs/get-started.md, docs/api-reference.md, docs/config-reference.md, docs/architecture.md, docs/troubleshooting.md and ci/validate_docs.py; added contract frontmatter to README.md, README_CN.md, AGENTS.md, CLAUDE.md, plan.md and docs/api.md.

## 0.5.10

- Web UI (issue #28): four browser pages (Dashboard / Modeling / Risk & Compliance / Copilot) served by the same FastAPI app at `/ui`; `/ws/*` auth accepts an `api_key` query parameter; `/ui` exempt from API-key and rate-limit middleware. See README.md for the full history of prior releases.
