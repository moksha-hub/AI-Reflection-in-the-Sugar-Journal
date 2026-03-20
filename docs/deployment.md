# Deployment Notes

The prototype supports three practical backend paths:

## 1. Mock backend

Use this for local development, CI, endpoint testing, and early Sugar-side integration.

- no external service required
- deterministic behavior
- safest default for testing UI wiring

## 2. Local Ollama

Use this when evaluating bounded one-question prompting on a local device.

- keeps data on the machine
- useful for latency and prompt-compliance experiments
- should be evaluated with small instruction-tuned models first

For this project, model selection should be evidence-driven:

- single-question compliance
- acceptable latency
- low fallback rate
- stable behavior across target locales

## 3. Sugar-AI

Use this when local hardware is too weak for reliable inference or when a deployment already runs Sugar-AI on a local or LAN-backed server.

- avoids making cloud inference part of the core student-facing design
- keeps the prototype aligned with current Sugar Labs infrastructure

## Readiness and health

The service exposes:

- `GET /health` for process-level liveness
- `GET /ready` for backend readiness

`/ready` is meant to answer a narrower question: can the currently configured backend serve requests now?

## Why cloud is not core

The codebase keeps a compatibility-oriented cloud backend, but the project does not depend on it. The main supported paths are local mock, local Ollama, and Sugar-AI.
