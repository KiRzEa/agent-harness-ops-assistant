# Notification Service Runbook
Tags: notification-service, email, sms

## Symptoms of degradation
Growing queue depth, delivery success below 98%, or provider rate limit errors.

## First response
Inspect the queue depth dashboard and the email or SMS provider status. Scale consumers up when the queue grows but the provider is healthy.

## Escalation
Delayed password reset emails are treated as a medium severity incident.
