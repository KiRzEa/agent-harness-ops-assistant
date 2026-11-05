# Database Failover Procedure
Tags: database, failover

## When to fail over
Primary unreachable for more than 2 minutes, or storage failure on the primary. Do not fail over for replica lag alone.

## Steps
Confirm the primary is truly down, promote the most up to date replica, update the connection endpoint, then verify writes succeed. Reconfigure the old primary as a replica after recovery.
