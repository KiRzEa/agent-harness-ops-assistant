# Inventory Service Runbook
Tags: inventory-service, inventory, database

## Symptoms of degradation
Replica lag above 30 seconds, stale stock counts, or overselling reports.

## First response
Check replica lag and long running queries on the primary. Pause the nightly batch import if it is running. Route reads to the primary only if lag stays above 60 seconds.

## Escalation
Overselling affecting customers is a high severity incident. Page the data platform on-call.
