# ADR 0003: Use RFC 9457-compatible Problem Details

Status: accepted

All HTTP failures use application/problem+json with the RFC 9457 fields type, title, status,
detail, and instance plus stable code and request_id extension members. Core application errors do
not depend on HTTP classes. Bootstrap is the only place that maps them to status codes.

This makes client error handling stable while allowing unknown implementation failures to be
logged internally with a stack trace and returned to clients as a safe generic response.
