# Search Service Runbook
Tags: search-service, search

## Symptoms of an outage
Health check failing, empty search results, or index nodes unreachable.

## First response
Check the cluster node status and disk usage on index nodes. Restart unhealthy nodes one at a time and wait for shard recovery before the next restart.

## Mitigation
Enable the cached results fallback so the storefront keeps showing recent popular searches. An outage longer than 15 minutes requires a high severity incident and a status page update.
