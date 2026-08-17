# ADR 0001: Use a modular monolith

Status: accepted

Spacewhy begins as one deployable FastAPI service with vertically sliced business modules. This
keeps transactions, deployment, observability, and developer workflows simple while preserving
clear future bounded-context ownership. Modules expose explicit public contracts and do not import
each other's infrastructure or ORM models.

Microservices, shared databases, and distributed transactions are deferred until a real product
and operational need proves that a module must be independently deployed.
