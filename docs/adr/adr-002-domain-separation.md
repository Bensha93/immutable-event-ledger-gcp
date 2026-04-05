# ADR-002 — Domain Separation Strategy

| Field | Detail |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-04-05 |
| **Decision Type** | Foundational Architectural Principle |
| **Applies To** | Immutable Event Ledger Architecture (GCP) |

---

## 1. Context

The system implements an immutable, event-driven ledger architecture on Google Cloud Platform (GCP). As the platform evolved, it became necessary to formally define domain boundaries to prevent cross-domain coupling and ensure long-term scalability, correctness, and auditability.

In distributed financial and operational systems, domain conflation often results in:

- Financial state corruption due to operational retries
- Tight coupling between business workflows and accounting records
- Inability to independently scale components
- Increased blast radius during failure
- Reduced audit integrity

To mitigate these risks, we must explicitly define domain separation rules at the architectural level.

This ADR formalises the domain separation model used in the platform.

---

## 2. Decision

The system **SHALL** enforce strict separation between the following domains:

1. Operational Domain
2. Financial Ledger Domain
3. Event Processing Domain

Each domain has independent responsibilities, storage boundaries, and processing logic.

> Cross-domain interaction is permitted only through well-defined immutable events.

---

## 3. Domain Definitions

### 3.1 Operational Domain

**Purpose:** Captures business activity events as they occur.

**Characteristics:**

- Append-only event storage
- No destructive updates
- Represents real-world actions (orders, adjustments, state changes, etc.)
- Optimised for business process traceability

**Constraints:**

- Operational records **MUST NOT** be mutated to reflect accounting corrections
- Corrections are represented via compensating operational events

### 3.2 Financial Ledger Domain

**Purpose:** Maintains accounting truth derived from operational events.

**Characteristics:**

- Immutable double-entry ledger
- Balanced debit/credit enforcement at processing time
- Append-only journal entries
- Partitioned by processing timestamp for analytical efficiency

**Constraints:**

- Ledger entries **MUST NEVER** be updated or deleted
- Financial corrections **MUST** be represented via compensating journal entries
- Ledger state is a projection, not a mutable record

### 3.3 Event Processing Domain

**Purpose:** Transforms operational events into financial ledger entries and projections.

**Characteristics:**

- Asynchronous processing
- At-least-once delivery semantics
- Idempotent event handling
- Outbox pattern for reliable event emission

**Constraints:**

- Processor **MUST** be stateless with respect to business state
- Processor **MUST NOT** directly mutate operational records
- Idempotency guarantees **MUST** be enforced

---

## 4. Architectural Rules

The following rules are mandatory:

### Rule 1 — No Cross-Domain Writes

Operational services **MUST NOT** write directly to ledger tables. Ledger entries are produced exclusively by the ledger processor.

### Rule 2 — Event as Contract

All cross-domain communication **SHALL** occur via immutable event contracts.

Event schemas are versioned and stored under:

```
schemas/
```

Events are considered the source of truth for all state transitions.

### Rule 3 — Immutability Enforcement

- No `UPDATE` statements on ledger tables
- No `DELETE` statements on operational event tables
- Corrections are implemented via compensating events

> Immutability guarantees audit integrity.

### Rule 4 — Independent Scalability

Domains **MUST** scale independently:

- Operational ingestion scales with traffic
- Ledger processing scales with financial throughput
- Analytical queries scale via partitioning and clustering

No domain may introduce a runtime dependency that blocks another domain.

---

## 5. Benefits

This separation model enables:

- Strong financial integrity
- Full audit traceability
- Reduced blast radius of failures
- Independent horizontal scaling
- Clear ownership boundaries
- Simplified reasoning about system state
- Enterprise-grade compliance readiness

---

## 6. Trade-Offs

### Increased Complexity

Domain separation introduces:

- Additional services
- Asynchronous processing latency
- More infrastructure components

This complexity is intentional and aligned with long-term system durability.

### Eventual Consistency

Because processing is asynchronous, the system is eventually consistent between operational and financial states.

> This is an acceptable trade-off for integrity and scalability.

---

## 7. Alternatives Considered

### A. Single Unified Domain — Rejected

Combining operational and financial logic into a single service.

Rejected because:

- Creates tight coupling
- Compromises audit guarantees
- Increases risk of state corruption
- Limits independent scaling

### B. Mutable Ledger Model — Rejected

Allowing updates to ledger entries.

Rejected because:

- Violates accounting principles
- Reduces traceability
- Compromises regulatory defensibility

---

## 8. Long-Term Architectural Implications

This ADR establishes a foundation for:

- Cross-domain reconciliation engines
- Advanced anomaly detection layers
- Governance auditing services
- Multi-tenant domain isolation
- Future regulatory compliance layers

> Domain separation is a non-reversible architectural commitment.

---

## 9. Enforcement Mechanisms

The following technical controls enforce this ADR:

| Control | Description |
|---|---|
| IAM restrictions | Prevent cross-domain writes at the infrastructure level |
| Database permissions | Limit `UPDATE` / `DELETE` access on ledger and event tables |
| Code review rules | Disallow mutable ledger logic at the PR level |
| Idempotency constraints | Enforced in the processing layer for all event handlers |
| Event schema versioning | Controlled schema evolution with backward compatibility |

---

## 10. Conclusion

Domain separation is a foundational principle of this architecture.

By enforcing strict boundaries between operational activity, financial accounting, and processing logic, the system achieves:

- Immutable audit guarantees
- Scalable event-driven processing
- Enterprise-grade integrity discipline

This decision aligns with long-term architectural durability and reflects industry-grade distributed system design practices.