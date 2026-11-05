# Checkout Service Runbook
Tags: checkout-service, checkout

## Symptoms of degradation
Cart abandonment spikes, 5xx from the checkout endpoint, or slow calls to payments-api.

## First response
Check payments-api and inventory-service status first, since checkout depends on both. Enable the degraded checkout mode, which skips live stock validation, only if inventory-service is down.

## Escalation
Open a high severity incident if checkout success rate drops below 90% for 10 minutes.
