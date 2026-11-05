# Payments API Runbook
Tags: payments-api, payments

## Symptoms of degradation
Card authorization error rate above 2%, p95 latency above 1.5s, or timeouts from checkout-service.

## First response
Check the payment provider status page, then the payments-api dashboard for error breakdown by provider. If the error rate stays above 2% for 10 minutes, open a high severity incident and page the payments on-call.

## Mitigation
Switch the traffic split to the secondary payment provider using the `payments-failover` toggle. Roll back the latest deployment if errors began right after a release.
