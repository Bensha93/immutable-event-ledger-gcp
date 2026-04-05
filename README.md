# Immutable Event-Driven Ledger on Google Cloud

## Overview

This repository demonstrates the design and implementation of an immutable, event-driven financial ledger built on Google Cloud Platform (GCP).

The project showcases enterprise-grade data architecture patterns designed for scalability, auditability, and long-term integrity.

It is not a CRUD-based accounting demo.
It is an architectural showcase of immutable financial processing principles.

---

## Architectural Goals

The system is designed around the following principles:

- Immutability-first data modeling
- Event-driven processing
- Strict domain separation
- Deterministic ledger state reconstruction
- Idempotent asynchronous processing
- Multi-tenant ready schema design
- Cost-efficient BigQuery partitioning & clustering

---

## Core Design Principles

### 1. Immutability

Financial records are never updated or deleted.
All state transitions are represented as new events.

This ensures:

- Auditability
- Traceability
- Replay capability
- Deterministic balance reconstruction

---

### 2. Domain Separation

Operational events and financial ledger entries are strictly separated.

| Domain | Responsibility |
|--------|---------------|
| Operational Domain | Business activity events |
| Financial Domain | Double-entry ledger records |
| Processing Domain | Asynchronous event handling |

This prevents financial drift and enforces reconciliation discipline.

---

### 3. Event-Driven Processing

All ledger updates are derived from immutable events.

An Outbox pattern ensures:

- Atomic write of state + event
- At-least-once delivery
- Idempotent processing
- Failure recovery without data corruption

---

### 4. Deterministic Ledger State

Ledger balances are reproducible from event history.

No mutable balance fields exist in the ledger.
Balances are derived from summation of journal entries.

---

### 5. BigQuery Optimization Strategy

Ledger and event tables are:

- Partitioned by `processed_at`
- Clustered by `tenant_id`

This ensures:

- Time-based query performance
- Reduced scan costs
- Multi-tenant scalability
- Governance-friendly isolation

---

## Technology Stack

- Google BigQuery (Partitioning, Clustering)
- Cloud Run (Microservices)
- Firestore (Transactional Event Store)
- Pub/Sub (Optional Event Queue)
- Python (Processing Logic)
- Docker (Containerization)

---

## Repository Structure

Here’s your structure cleaned up into a **Markdown-friendly, properly formatted directory tree** (ready for README or docs):



```
immutable-event-ledger-gcp/

├── README.md
│
├── docs/
│   ├── architecture-overview.md
│   ├── adr-001-event-driven-ledger.md
│   ├── adr-002-domain-separation.md
│   └── architecture-diagram.png
│
├── sql/
│   ├── 001_create_ledger_tables.sql
│   ├── 002_create_events_table.sql
│   ├── 003_partitioning_strategy.sql
│   └── sample_queries.sql
│
├── services/
│   ├── ingestion_service.py
│   ├── ledger_processor.py
│   └── outbox_worker.py
│
├── schemas/
│   ├── ledger_event_schema.json
│   └── operational_event_schema.json
│
├── docker/
│   └── Dockerfile
│
└── examples/
├── sample_event.json
└── example_flow.md

```


### Notes

- **docs/** → Architecture decisions and system design documentation  
- **sql/** → BigQuery schema definitions and queries  
- **services/** → Core processing services (ingestion, ledger processing, async workers)  
- **schemas/** → JSON schema contracts for events  
- **docker/** → Containerization setup for deployment  
- **examples/** → Sample data and workflow demonstrations  

---

## Example Flow

1. Operational event is received (e.g., transaction created)
2. Event is stored immutably
3. Outbox entry is created atomically
4. Worker processes event asynchronously
5. Double-entry ledger entries are generated
6. Ledger remains append-only

---

## Why This Architecture Matters

Traditional systems:
- Mutate balances
- Overwrite records
- Create reconciliation risk

This architecture:
- Preserves financial truth
- Supports audit and replay
- Enables cross-domain reconciliation
- Is ready for regulatory-grade environments

---

## What This Project Demonstrates

- Enterprise-grade event sourcing patterns
- Immutable financial modeling
- Governance-aware data architecture
- Multi-tenant scalable data design
- Idempotent distributed processing
- Cost-efficient BigQuery schema strategy

---

## Important Notes

This repository focuses on architectural patterns and ledger design principles.

It does not represent a full commercial system.
It is intended as a portfolio demonstration of scalable, governance-first data engineering practices.

---

## Author

Designed and implemented as part of an enterprise-grade data architecture portfolio focused on integrity-driven system design.
