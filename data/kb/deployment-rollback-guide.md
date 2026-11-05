# Deployment Rollback Guide
Tags: deployment, rollback

## When to roll back
Errors or latency began within 30 minutes of a release and the release is the likeliest cause.

## Steps
Identify the previous stable version, trigger the rollback pipeline, watch error rate for 10 minutes, and block the bad release from redeploying. Record the rollback in the incident timeline.
