# ADR-001 — Event-Driven Immutable Ledger on GCP

| Field | Detail |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-04-05 |
| **Author** | Data Architecture |
| **Decision Type** | Foundational Architectural Decision |

---

## 1. Context

Modern distributed systems require strong guarantees around financial integrity, traceability, and auditability. Traditional CRUD-based data models introduce risks in financial systems, including:

- Destructive updates to financial records
- Loss of historical traceability
- Hidden reconciliation discrepancies
- Tight coupling between operational state and accounting state
- Limited audit defensibility

In regulated, investor-facing, or financially sensitive environments, mutable financial records are unacceptable.

To address these risks, this project establishes an event-driven, append-only financial ledger architecture implemented on Google Cloud Platform (GCP).

This decision forms the backbone of the system's financial integrity model.

---

## 2. Decision

We will implement the financial ledger as:

> **An Immutable, Event-Driven, Double-Entry Ledger**

With the following properties:

### 2.1 Append-Only Ledger Entries

- Ledger records are never updated
- Ledger records are never deleted
- Corrections are implemented via compensating entries

### 2.2 Event-Driven Processing

- Financial entries are derived from domain events
- Events are processed asynchronously
- Processing follows at-least-once delivery semantics
- Idempotency is enforced at the ledger processing layer

### 2.3 Double-Entry Accounting Enforcement

- Every financial transaction must produce balanced debit and credit entries
- Ledger processor validates accounting equality before commit
- Unbalanced transactions are rejected

### 2.4 Separation of Concerns

- Operational events are distinct from ledger entries
- Financial truth is derived, not directly written by external systems

### 2.5 Partitioned & Scalable Storage (BigQuery)

- Ledger tables are partitioned by `processed_at`
- Clustered by `tenant_id` for multi-tenant scalability
- Optimised for audit, reconciliation, and analytical workloads

---

## 3. Architecture Pattern

The ledger follows this processing model:

```mermaid
flowchart LR
    A([Operational Event]) --> B[(Event Store)]
    B --> C[Outbox]
    C --> D[Ledger Processor]
    D --> E[(Ledger Entries)]

    style A fill:#1565C0,color:#fff,stroke:#0d47a1
    style B fill:#E65100,color:#fff,stroke:#BF360C
    style C fill:#2E7D32,color:#fff,stroke:#1B5E20
    style D fill:#6A1B9A,color:#fff,stroke:#4A148C
    style E fill:#006064,color:#fff,stroke:#004D40
```

### Components

**Operational Events Table**
- Stores immutable business events
- Source of truth for all business actions

**Outbox Pattern**
- Guarantees reliable event delivery
- Prevents partial failure between state change and event emission

**Ledger Processor Service**
- Stateless microservice
- Consumes pending events
- Applies accounting logic
- Enforces double-entry constraints
- Writes immutable ledger rows

**Ledger Tables**
- Append-only
- Optimised for time-based partitioning
- Structured for reconciliation and auditing

---

## 4. Design Principles

### 4.1 Immutability

Financial records must never be altered post-write.

If a correction is required:

- A compensating ledger entry must be issued
- The original record remains intact
- The audit chain remains preserved

> This guarantees historical defensibility.

### 4.2 Idempotency

Given at-least-once delivery semantics, duplicate event processing is possible. The ledger processor enforces idempotency using:

- Unique `ledger_event_id`
- Deterministic processing keys
- Deduplication checks before insertion

> This ensures financial accuracy under retry conditions.

### 4.3 Double-Entry Discipline

For every transaction:

```
Σ(debits) = Σ(credits)
```

Ledger processor validation ensures:

- Atomic balance enforcement
- Rejection of malformed financial transformations
- Accounting integrity at ingestion time

### 4.4 Multi-Tenant Scalability

All ledger records include:

- `tenant_id`
- `ledger_event_id`
- `processed_at`

Partitioning by time enables:

- Efficient audit queries
- Cost-controlled scanning
- High-performance historical analysis

Clustering by `tenant_id` enables:

- Tenant isolation
- Efficient tenant-scoped reporting
- Scalable growth

---

## 5. Alternatives Considered

### A. Mutable Ledger Rows (Update-Based Model)

**Rejected** due to:

- Audit risk
- Historical traceability loss
- Regulatory exposure
- Increased fraud surface area

### B. Direct Writes to Ledger from External Systems

**Rejected** due to:

- Lack of accounting validation enforcement
- Tight coupling to upstream systems
- Integrity risk

### C. Event-Sourced Ledger (Full Replay Model)

**Deferred.**

While event sourcing provides strong replay guarantees, this implementation focuses on:

- Derived immutable ledger entries
- Separation between event store and financial store
- Optimised analytical storage

A future ADR may revisit full replay architecture if regulatory requirements demand it.

---

## 6. Consequences

### Positive

- Strong financial integrity guarantees
- Audit defensibility
- Clear separation between operational and financial truth
- Scalable for high transaction volume
- Supports reconciliation frameworks
- Enables advanced anomaly detection downstream

### Tradeoffs

- Increased architectural complexity
- Asynchronous processing latency
- Additional microservice management overhead
- Strong dependency on idempotency correctness

---

## 7. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Duplicate event processing | Idempotent ledger processor |
| Partial failure | Outbox pattern |
| Financial imbalance | Double-entry validation |
| Cross-tenant leakage | Row-Level Security + tenant clustering |
| Query cost explosion | Time partitioning |

---

## 8. Compliance & Audit Considerations

The immutable ledger model supports:

- Regulatory reporting
- Forensic traceability
- Transaction lineage reconstruction
- Historical financial state verification

> No destructive mutations ensures long-term audit confidence.

---

## 9. Implementation References

| File | Description |
|---|---|
| `sql/001_create_ledger_tables.sql` | Ledger table definitions |
| `sql/003_partitioning_strategy.sql` | Partitioning and clustering configuration |
| `services/ledger_processor.py` | Core ledger processing service |
| `services/outbox_worker.py` | Outbox polling and event relay |
| `schemas/ledger_event_schema.json` | Canonical event schema definition |