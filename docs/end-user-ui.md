# End-User Interface

Verified: 2026-06-07

The first user interface is a local, dependency-free lab console. It is intentionally small: it lets a user select a capture, create a planned pipeline job, inspect stage gates and see commercial/compliance status before heavy reconstruction work starts.

## Scope

The UI owns:

- capture selection from tracked manifests
- job planning through the existing pipeline contract
- pipeline gate visibility
- commercial/compliance visibility
- local RTX workstation status evidence

The UI does not own:

- video decoding
- SfM
- splat training
- artifact conversion
- viewer runtime validation

Those remain separate stages and must keep their own reports.

## Runtime

The first implementation uses only:

- Python standard library HTTP server
- browser HTML/CSS/JavaScript APIs
- tracked JSON manifests

No npm package, CDN, external UI framework or hosted service is required for this first UI. This keeps the commercial dependency surface small until the framework/compliance gate approves a richer frontend stack.

## Commands

Start the local UI:

```bash
./scripts/lab-ui-server.py
```

Validate the UI contract:

```bash
./scripts/validate-ui-contracts.sh
```

Default local URL:

```text
http://127.0.0.1:8765
```

## Promotion Rule

A future React/Vite or richer app can replace this UI only after:

- dependency licenses are recorded in `framework-evaluation.json`
- npm dependency tree is scanned
- notices are collected
- the app still creates jobs through the pipeline contract
- generated artifacts stay out of git
