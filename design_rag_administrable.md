# RAG Administrable System Design

## Overview
Make RAG configurations administrable via API, similar to agents. RAG configurations are independent entities that agents can reference.

## Database Changes

### New Table: `rag_configs`
Columns:
- `id` UUID primary key
- `user_id` UUID foreign key to users (on delete CASCADE)
- `name` VARCHAR(255) not null
- `description` TEXT
- `provider_type` VARCHAR(20) not null (enum: 'vectorbase', 'saas_rag')
- `provider` VARCHAR(50) not null (e.g., "qdrant.internal", "pinecone.io", "rag.saas")
- `provider_config` JSONB not null (provider-specific configuration)
- `is_default` BOOLEAN default false
- `is_active` BOOLEAN default true
- `created_at` TIMESTAMP with time zone
- `updated_at` TIMESTAMP with time zone

Indexes:
- `idx_rag_configs_user_id` (user_id)
- `idx_rag_configs_is_default` (is_default) where is_default = true
- `idx_rag_configs_user_default` (user_id) unique where is_default = true

### Update Table: `agents`
Add column:
- `rag_config_id` UUID nullable foreign key to rag_configs (on delete SET NULL)

## Provider Registry Extension

Extend `ProviderRegistry` to support "rag" provider type with two sub‑types.

### Provider Types

#### 1. Vectorbase (we manage in voicebot‑app)
- **qdrant.internal** (internal Qdrant service)
   - Expected properties: `collection_name`, `embed_model_name`, `reranker_model`, `top_k`, etc.
   - Non‑configurable parameters (host, port, API key, TLS) are stored in `provider_constants.json`.
- **pinecone.io** (cloud vector database)
   - Expected properties: `api_key`, `environment`, `index_name`, `project_id`, `collection_name`, `embed_model_name`, `top_k`, etc.
   - Non‑configurable parameters (URL, port) are stored in `provider_constants.json`.

#### 2. SaaS RAG (we do not manage in voicebot‑app)
- **rag.saas** (placeholder for future SaaS RAG services)
   - Expected properties: `api_key` only.
   - Non‑configurable parameters (URL, port) are stored in `provider_constants.json`.

### Provider Interface
Each provider class must implement:
- `get_expected_properties()` -> List[str]
- `get_field_definitions()` -> Dict[str, Dict]
- `create_client(config: Dict) -> Any` (optional)
- `query(client, text, top_k, namespace) -> List[Context]`
- `ingest(client, documents) -> int`
- `delete(client, document_ids) -> bool`

### Provider Constants
Add a new section `rag` in `src/services/provider_constants.json` to store non‑configurable parameters (URL, port, etc.) per provider.

## Service Layer

### RagConfigService
CRUD operations for RAG configurations, similar to AgentService.

### RagRuntimeService
Factory that creates a RAG client based on provider configuration, caches connections, and provides retrieval methods.

## API Routes

### RAG Configuration Management
- `POST /api/rag-configs` create
- `GET /api/rag-configs` list
- `GET /api/rag-configs/{id}` get
- `PUT /api/rag-configs/{id}` update
- `DELETE /api/rag-configs/{id}` delete
- `POST /api/rag-configs/{id}/set-default` set as default

### RAG Operations (per configuration)
- `POST /api/rag-configs/{id}/query` query with text
- `POST /api/rag-configs/{id}/ingest` ingest documents
- `DELETE /api/rag-configs/{id}/documents` delete documents

## Integration with Agents

Agent model gets `rag_config_id` foreign key. When an agent is used in voicebot, if `rag_config_id` is set and RAG is enabled, use that RAG configuration for retrieval.

## Frontend Changes

- Add RAG configuration management page (list, create, edit) similar to agents.
- In agent creation/edit, add dropdown to select RAG configuration.
- UI should first let user choose provider type (vectorbase / SaaS RAG), then provider, then show appropriate configuration fields.

## Performance Considerations

- Cache RAG clients per configuration to avoid re‑initialization.
- Preload embedding models for internal Qdrant provider.
- Support ultra‑low latency mode with minimal configuration.

## Migration Steps

1. Create alembic migration for `rag_configs` table and `agents.rag_config_id` column.
2. Update `src/database/models.py`.
3. Extend provider registry and add `rag` section to `provider_constants.json`.
4. Implement RagConfigService and routes.
5. Update agent service to handle RAG configuration.
6. Update frontend components.
7. Write tests.

## Next Steps

Approve this design, then switch to code mode to implement.