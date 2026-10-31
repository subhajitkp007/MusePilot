# Security & Responsible AI Policy

## Secret Management & Privacy

- **Zero Secrets in Code:** All API keys (`MUSEPILOT_META_API_KEY`, `MUSEPILOT_PARTNER_API_KEY`) must be supplied strictly via environment variables or `.env` (which is git-ignored and docker-ignored).
- **Automatic PII & Credential Redaction:** `musepilot.telemetry.redaction` automatically scrubs bearer tokens, API keys, passwords, and sensitive step payloads before any log record or JSON trace is written to disk.
- **Local-First Trace Storage:** Recorded screen frames and execution traces stay on the local filesystem unless explicitly transmitted to configured model inference endpoints.

## Responsible AI Guardrails

1. **Action Allowlist:** MusePilot restricts input events to the active target application bounding box and allowed operations (`click`, `type`, `drag`, `wait`, `verify`).
2. **Destructive Action Confirmation:** Steps flagged as destructive (`delete`, `purchase`, `external_submit`) require explicit human-in-the-loop confirmation before execution.
3. **Graceful Human Escalation:** When visual verification fails after the configured retry and replan budget, the orchestrator halts execution and highlights the ambiguous screen region for the human operator.

