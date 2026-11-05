# Cache Flush Procedure
Tags: cache, redis

## When to flush
Only when stale data is confirmed and a targeted key deletion is not possible.

## Steps
Flush one region at a time and watch database load, since a full flush causes a surge of cache misses. Never flush during peak traffic without approval from the incident commander.
