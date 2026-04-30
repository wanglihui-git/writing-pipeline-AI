---
name: sync-api-readme-examples
description: Keep API docs aligned with implementation by updating README.md API examples whenever any API endpoint is added, modified, renamed, or removed. Use when editing FastAPI routes, request/response contracts, or endpoint behavior.
---

# Sync API README Examples

## Purpose

Ensure `README.md` always reflects the current debuggable API surface.

## When To Apply

Apply this skill whenever any endpoint is added/modified/removed in files under:

- `app/api/routes/`
- `app/api/main.py`
- Any service/model change that affects API request or response shape

## Required Actions

1. Update `README.md` section `5.4 API 调试接口（每个接口至少一个示例）`.
2. Keep the top-level API list in `README.md` section `1. 功能概览` in sync.
3. For each changed endpoint, provide at least one runnable example command.
4. If an endpoint is removed, remove or mark its example accordingly.
5. Keep endpoint order readable and numbering consecutive in section 5.4.

## Example Checklist

Copy this checklist when changing APIs:

```text
- [ ] API route implementation updated
- [ ] README section 1 API list updated
- [ ] README section 5.4 example added/updated/removed
- [ ] Example request body/params reflect latest schema
- [ ] Endpoint numbering remains consecutive
```

## Conventions

- Use PowerShell `curl` examples, matching the repository style.
- Use default base URL: `http://127.0.0.1:8980`.
- Use placeholder IDs like `<task_id>` and `<job_id>`.
