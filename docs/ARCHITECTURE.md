# ARCHITECTURE.md - Component and Infrastructure Diagrams

## System Context Diagram

```mermaid
graph TB
    subgraph "External Actors"
        Customer[Customer<br/>Web/Chat/Email]
        Agent[Support Agent<br/>Dashboard]
        Manager[Support Manager<br/>Admin UI]
    end

    subgraph "Platform"
        GW[API Gateway<br/>Kong/Envoy]
        Auth[Auth Service<br/>OIDC, RBAC]
        Ingest[Ingestion Service]
        Orch[Orchestration Service<br/>LangGraph]
        Knowledge[Knowledge Service<br/>RAG Pipeline]
        Action[Action Executor<br/>MCP Tools]
        Memory[Memory Service]
        Admin[Admin Service]
        Notify[Notification Service]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 16<br/>+ pgvector)]
        Redis[(Redis 7<br/>Cluster)]
        Vector[(Vector DB<br/>Weaviate/Qdrant)]
        S3[(Object Storage<br/>S3/Blob/GCS)]
        Kafka[(Event Bus<br/>Kafka/MSK)]
        Search[(OpenSearch)]
    end

    subgraph "External Integrations"
        ZD[Zendesk]
        IC[Intercom]
        SN[ServiceNow]
        SG[SendGrid/SES]
        Stripe[Stripe/Billing]
        CRM[Salesforce/HubSpot]
        Telemetry[Segment/Mixpanel]
        Slack[Slack/Teams]
        PD[PagerDuty]
        IdP[Okta/Azure AD]
    end

    Customer --> GW
    Agent --> GW
    Manager --> GW
    GW --> Auth
    GW --> Ingest
    GW --> Orch
    GW --> Admin
    GW --> Notify

    Ingest --> Kafka
    Orch --> Knowledge
    Orch --> Action
    Orch --> Memory
    Orch --> Kafka

    Knowledge --> Vector
    Knowledge --> Search
    Action --> PG
    Memory --> PG
    Memory --> Redis
    Memory --> Vector
    Admin --> PG
    Admin --> Redis
    Notify --> Slack
    Notify --> PD
    Notify --> SG

    PG --> Kafka
    Redis --> Kafka
    Vector --> Kafka
    S3 --> Kafka

    Ingest -.-> ZD
    Ingest -.-> IC
    Ingest -.-> SN
    Ingest -.-> SG
    Action -.-> Stripe
    Action -.-> CRM
    Orch -.-> Telemetry
    Auth -.-> IdP
```

## Container Diagram (C4 Level 2)

```mermaid
graph TB
    subgraph "Client Applications"
        Chat[Web Chat Widget]
        InApp[In-App Widget]
        Console[Agent Console<br/>Next.js]
    end

    subgraph "Edge"
        GW[API Gateway<br/>Kong/Envoy<br/>Auth, Rate Limit, WAF]
    end

    subgraph "Services"
        AuthSvc[Auth Service<br/>FastAPI]
        IngestSvc[Ingestion Service<br/>FastAPI]
        OrchSvc[Orchestration Service<br/>FastAPI + LangGraph]
        AdminSvc[Admin Service<br/>FastAPI]
        AgentWorkers[Agent Workers<br/>Python + LangGraph]
        ActionSvc[Action Executor<br/>FastAPI]
        KnowledgeSvc[Knowledge Service<br/>FastAPI + RAG]
        MemorySvc[Memory Service<br/>FastAPI]
        NotifySvc[Notification Service<br/>FastAPI]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 16)]
        Redis[(Redis 7)]
        VectorDB[(Vector DB)]
        ObjStore[(Object Storage)]
        EventBus[(Kafka)]
        SearchIdx[(OpenSearch)]
    end

    Chat --> GW
    InApp --> GW
    Console --> GW

    GW --> AuthSvc
    GW --> IngestSvc
    GW --> OrchSvc
    GW --> AdminSvc

    IngestSvc --> EventBus
    OrchSvc --> AgentWorkers
    OrchSvc --> ActionSvc
    OrchSvc --> KnowledgeSvc
    OrchSvc --> MemorySvc
    OrchSvc --> EventBus

    AgentWorkers --> KnowledgeSvc
    AgentWorkers --> MemorySvc
    ActionSvc --> PG
    KnowledgeSvc --> VectorDB
    KnowledgeSvc --> SearchIdx
    MemorySvc --> PG
    MemorySvc --> Redis
    MemorySvc --> VectorDB
    AdminSvc --> PG
    AdminSvc --> Redis
    NotifySvc --> EventBus
```

## Component Diagram - Orchestration Service

```mermaid
graph TB
    subgraph "Orchestration Service"
        API[FastAPI Endpoints]
        Graph[LangGraph StateGraph]
        Checkpoint[Redis Checkpointing]
    end

    subgraph "Agent Nodes"
        Supervisor[Supervisor Agent]
        Customer[Customer Agent]
        Knowledge[Knowledge Agent]
        Troubleshooting[Troubleshooting Agent]
        Resolution[Resolution Agent]
        Escalation[Escalation Agent]
        HumanApproval[Human Approval Node]
    end

    subgraph "Shared State"
        State[(SupportState<br/>TypedDict)]
    end

    API --> Graph
    Graph --> Checkpoint
    Graph --> State

    Graph --> Supervisor
    Supervisor --> Customer
    Supervisor --> Knowledge
    Supervisor --> Troubleshooting
    Supervisor --> Resolution
    Supervisor --> Escalation
    Supervisor --> HumanApproval

    Customer --> State
    Knowledge --> State
    Troubleshooting --> State
    Resolution --> State
    Escalation --> State
    HumanApproval --> State
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant C as Customer
    participant GW as API Gateway
    participant ING as Ingestion
    participant KAFKA as Kafka
    participant SUP as Supervisor
    participant CA as Customer Agent
    participant KA as Knowledge Agent
    participant TA as Troubleshooting
    participant RA as Resolution Agent
    participant AE as Action Executor
    participant MEM as Memory
    participant PG as PostgreSQL
    participant REDIS as Redis

    C->>GW: Submit support request
    GW->>ING: Forward (authenticated)
    ING->>ING: Normalize, dedupe
    ING->>KAFKA: SupportRequest event
    KAFKA->>SUP: Trigger workflow
    SUP->>CA: Analyze request
    CA->>REDIS: Get customer context (cache)
    alt Cache miss
        CA->>PG: Query customer profile
        PG-->>CA: Customer 360°
        CA->>REDIS: Cache context (15min TTL)
    end
    CA-->>SUP: Intent, entities, severity
    SUP->>KA: Retrieve knowledge
    KA->>KA: Hybrid search (vector+BM25+graph)
    KA->>KA: RRF fusion
    KA->>KA: Cross-encoder rerank
    KA-->>SUP: Retrieved context + citations
    SUP->>TA: Diagnose
    TA-->>SUP: Hypotheses
    SUP->>RA: Generate resolution
    RA-->>SUP: Plan + response + confidence
    alt Confidence >= threshold
        SUP->>AE: Execute approved actions
        AE->>PG: Execute MCP tool
        PG-->>AE: Result
        AE-->>SUP: Action results
        SUP->>MEM: Store case + outcome
        MEM->>PG: Insert resolved_case (with embedding)
        SUP->>GW: Send response
        GW->>C: Resolution delivered
    else Confidence < threshold
        SUP->>SUP: Escalate to human
        SUP->>GW: Create handoff
        GW->>C: "Connecting you with an agent..."
    end
```

## Deployment Architecture (AWS Example)

```mermaid
graph TB
    subgraph "AWS Cloud (us-east-1)"
        subgraph "VPC"
            subgraph "Public Subnets"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
            end
            subgraph "Private Subnets - EKS"
                subgraph "Ingress"
                    NGINX[Nginx Ingress]
                end
                subgraph "Application"
                    API[API Services]
                    AGENTS[Agent Workers]
                    ACTIONS[Action Executor]
                end
                subgraph "Data"
                    RDS[(RDS PostgreSQL<br/>Multi-AZ)]
                    REDIS[ElastiCache Redis<br/>Cluster]
                    OS[OpenSearch]
                end
            end
            subgraph "Private Subnets - MSK"
                KAFKA[MSK Kafka]
            end
        end
        S3[S3 Bucket<br/>Versioned, Lifecycle]
        ECR[ECR Registry]
        SM[Secrets Manager]
        CW[CloudWatch]
    end
    subgraph "External"
        LLM[LLM APIs]
        ZD[Zendesk]
        SG[SendGrid]
    end
    ALB --> NGINX --> API
    API --> AGENTS
    AGENTS --> ACTIONS
    API --> RDS
    API --> REDIS
    AGENTS --> OS
    API --> KAFKA
    AGENTS --> LLM
    API --> ZD
    API --> SG
    API --> S3
```

## Kubernetes Namespace Layout

```yaml
# Namespace Structure
namespaces:
  - platform-system    # Istio, cert-manager, monitoring
  - auth               # Auth service, OIDC proxy
  - ingestion          # Channel adapters
  - orchestration      # LangGraph workflows
  - agents             # Agent workers (separate deployments per agent)
  - actions            # Action executor, approval service
  - knowledge          # RAG service, indexer
  - memory             # Memory service
  - admin              # Admin API, dashboard BFF
  - data               # PostgreSQL operator, Redis operator, Vector DB
  - observability      # OTel collector, Prometheus, Grafana, Loki
```

## Multi-Cloud Service Mapping

| Component | AWS | Azure | GCP |
|-----------|-----|-------|-----|
| Kubernetes | EKS | AKS | GKE |
| Container Registry | ECR | ACR | Artifact Registry |
| PostgreSQL | RDS | Azure Database | Cloud SQL |
| Redis | ElastiCache | Azure Cache | Memorystore |
| Vector DB | Pinecone/OpenSearch | Azure AI Search | Vertex AI Vector Search |
| Event Bus | MSK | Event Hubs (Kafka) | Pub/Sub |
| Object Storage | S3 | Blob Storage | Cloud Storage |
| Secrets | Secrets Manager | Key Vault | Secret Manager |
| CDN | CloudFront | Front Door | Cloud CDN |
| DNS | Route 53 | Azure DNS | Cloud DNS |
| IaC | Terraform | Terraform | Terraform |
| CI/CD | GitHub Actions | GitHub Actions | GitHub Actions |

## Security Layers

```mermaid
graph TB
    subgraph "Layer 1: Edge"
        WAF[WAF - OWASP Rules]
        DDoS[DDoS Protection]
        TLS[TLS 1.3 Termination]
        RateLimit[Rate Limiting]
        Bot[Bot Detection]
    end
    subgraph "Layer 2: Auth & AuthZ"
        OIDC[OIDC/SAML SSO]
        JWT[JWT - 15min TTL]
        MFA[MFA for Admin]
        RBAC[RBAC + ABAC]
        mTLS[mTLS - Istio]
    end
    subgraph "Layer 3: Application"
        Validation[Input Validation - Pydantic]
        Encoding[Output Encoding]
        CSRF[CSRF Protection]
        SQLi[SQLi Prevention - ORM]
        SSRF[SSRF Protection]
        SCA[Dependency Scanning]
    end
    subgraph "Layer 4: Data"
        EncRest[Encryption at Rest - AES-256]
        EncTransit[Encryption in Transit - TLS 1.3]
        FieldEnc[Field-level PII Encryption]
        Tokenization[Tokenization]
        RLS[Database RLS]
        Audit[Immutable Audit Logs]
    end
    subgraph "Layer 5: Infrastructure"
        PrivateSubnets[Private Subnets]
        SG[Security Groups/NSGs]
        Vault[Secrets Management]
        ImageScan[Image Scanning]
        Falco[Runtime Security - Falco]
        NetPol[K8s Network Policies]
    end
```

## Agent Communication Protocol

```mermaid
graph LR
    subgraph "LangGraph State (SupportState)"
        State[{
            ticket_id,
            tenant_id,
            messages[],
            customer{},
            intent,
            category,
            severity,
            sentiment,
            retrieved_docs[],
            hypotheses[],
            proposed_actions[],
            draft_response,
            confidence,
            is_escalated,
            next_node
        }]
    end

    Supervisor -->|Routes| Customer
    Supervisor -->|Routes| Knowledge
    Supervisor -->|Routes| Troubleshooting
    Supervisor -->|Routes| Resolution
    Supervisor -->|Routes| Escalation
    Supervisor -->|Routes| HumanApproval

    Customer -->|Writes: intent, entities, severity, customer| State
    Knowledge -->|Writes: retrieved_docs| State
    Troubleshooting -->|Writes: hypotheses| State
    Resolution -->|Writes: proposed_actions, draft_response, confidence| State
    Escalation -->|Writes: escalation_package| State
    HumanApproval -->|Writes: approval_result| State
```

---

*Diagrams are in Mermaid format. Render with any Mermaid-compatible viewer (GitHub, GitLab, VS Code, Notion, Obsidian).*