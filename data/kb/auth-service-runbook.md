# Auth Service Runbook
Tags: auth-service, login

## Symptoms of degradation
Login failures, token validation errors, or p95 latency above 500ms.

## First response
Check the identity database connection pool and the token signing key rotation job. Restart pods one at a time if connections are exhausted.

## Escalation
If users cannot log in for more than 5 minutes, open a critical incident and page the platform on-call.
