# High Latency Troubleshooting
Tags: latency, troubleshooting

## Quick checks
Compare p50 and p95 to find whether all requests or only the tail is slow. Check dependency latency, database slow queries, and recent deployments.

## Common causes
Exhausted connection pools, cache misses after a flush, noisy neighbors, and slow downstream providers.
