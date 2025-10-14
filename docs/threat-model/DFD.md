```mermaid
flowchart TB
    %% === Trust Boundaries ===
    subgraph Client["Client Boundary"]
        U[Пользователь / UI]
    end

    subgraph Edge["Edge / API Gateway"]
        GW[FastAPI Router / API Layer]
    end

    subgraph Core["Core Application"]
        SVC[Business Logic / Services]
    end

    subgraph Data["Data Boundary"]
        DB[(Storage / Decks & Cards DB)]
    end

    %% === Flows ===
    U -->|F1: Login request (JWT)| GW
    GW -->|F2: Validate credentials → issue token| SVC
    SVC -->|F3: Query user by email| DB
    GW -->|F4: CRUD decks/cards| SVC
    SVC -->|F5: Read/write decks & cards| DB
    GW -->|F6: Error responses (JSON)| U
    GW -->|F7: Metrics/logs| SVC
    SVC -->|F8: Audit / system logs| DB
