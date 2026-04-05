flowchart TB
    %% ==============================
    %% CLIENT & ENTRY LAYER
    %% ==============================

    subgraph Client_Layer["Client & Integration Layer"]
        A1[External Systems / Producers]
        A2[REST API Clients]
        A3[Batch Upload Sources]
    end

    subgraph Ingestion_Layer["Ingestion Layer (Cloud Run)"]
        B1[Ingestion Service]
        B2[Schema Validation]
        B3[Event Envelope Builder]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B2 --> B3

    %% ==============================
    %% EVENT STORE
    %% ==============================

    subgraph Event_Store["Immutable Event Store (BigQuery)"]
        C1[(Operational Events Table)]
        C2[(Financial Events Table)]
        C3[(Outbox Table)]
    end

    B3 --> C1
    B3 --> C3

    %% ==============================
    %% ASYNC PROCESSING LAYER
    %% ==============================

    subgraph Processing_Layer["Asynchronous Processing Layer"]
        D1[Outbox Worker]
        D2[Ledger Processor]
        D3[Idempotency Guard]
    end

    C3 --> D1
    D1 --> D3
    D3 --> D2
    D2 --> C2

    %% ==============================
    %% LEDGER & STORAGE LAYER
    %% ==============================

    subgraph Ledger_Layer["Financial Ledger (Partitioned & Clustered)"]
        E1[(Journal Entries)]
        E2[(Account Balances View)]
    end

    C2 --> E1
    E1 --> E2

    %% ==============================
    %% ANALYTICS & GOVERNANCE
    %% ==============================

    subgraph Governance_Analytics["Governance & Monitoring"]
        F1[Reconciliation Jobs]
        F2[Monitoring Queries]
        F3[Audit Views]
    end

    E1 --> F1
    C1 --> F1
    F1 --> F2
    E1 --> F3
    C1 --> F3

    %% ==============================
    %% INFRASTRUCTURE CONTROLS
    %% ==============================

    subgraph Infrastructure_Controls["Platform Controls"]
        G1[Row-Level Security]
        G2[Partition by processed_at]
        G3[Cluster by tenant_id]
        G4[Immutable Data Policy]
    end

    C1 --- G1
    C2 --- G1
    E1 --- G2
    E1 --- G3
    E1 --- G4
