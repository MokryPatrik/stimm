# Agent Management System - Phase Implementation Plans

## Phase 1: Database & Core Infrastructure

### Phase 1A: Database Setup
**Files to create/modify:**
- [`docker-compose.yml`](docker-compose.yml) - Add PostgreSQL service
- [`src/voicebot_app/database/__init__.py`](src/voicebot_app/database/__init__.py) - Database package
- [`src/voicebot_app/database/models.py`](src/voicebot_app/database/models.py) - SQLAlchemy models
- [`src/voicebot_app/database/session.py`](src/voicebot_app/database/session.py) - Database session management
- [`alembic.ini`](alembic.ini) - Alembic configuration
- [`alembic/env.py`](alembic/env.py) - Alembic environment
- [`alembic/versions/001_initial_agent_schema.py`](alembic/versions/001_initial_agent_schema.py) - Initial migration

**Implementation Steps:**
1. Add PostgreSQL service to docker-compose
2. Create database models (User, Agent, AgentSession)
3. Set up Alembic for database migrations
4. Run initial migration to create tables
5. Test database connectivity

### Phase 1B: Core Agent Services
**Files to create:**
- [`src/voicebot_app/services/agent/__init__.py`](src/voicebot_app/services/agent/__init__.py) - Agent package
- [`src/voicebot_app/services/agent/models.py`](src/voicebot_app/services/agent/models.py) - Pydantic models
- [`src/voicebot_app/services/agent/agent_service.py`](src/voicebot_app/services/agent/agent_service.py) - CRUD operations
- [`src/voicebot_app/services/agent/agent_manager.py`](src/voicebot_app/services/agent/agent_manager.py) - Runtime management
- [`src/voicebot_app/services/agent/exceptions.py`](src/voicebot_app/services/agent/exceptions.py) - Custom exceptions

**Implementation Steps:**
1. Implement AgentService with CRUD operations
2. Create AgentManager for runtime agent resolution
3. Add configuration caching for performance
4. Implement default agent creation from .env
5. Add comprehensive error handling

### Phase 1C: Integration & Testing
**Files to modify:**
- [`src/voicebot_app/main.py`](src/voicebot_app/main.py) - Add agent initialization on startup
- [`src/voicebot_app/requirements.txt`](src/voicebot_app/requirements.txt) - Add new dependencies
- Create test files in [`src/voicebot_app/services/agent/tests/`](src/voicebot_app/services/agent/tests/)

**Implementation Steps:**
1. Add agent initialization to main.py startup
2. Create default dev agent from .env configuration
3. Write unit tests for agent services
4. Test database operations and caching
5. Verify backward compatibility

---

## Phase 2: Service Integration & API

### Phase 2A: Service Factory Updates
**Files to modify:**
- [`src/voicebot_app/services/llm/llm.py`](src/voicebot_app/services/llm/llm.py) - Accept agent configuration
- [`src/voicebot_app/services/tts/tts.py`](src/voicebot_app/services/tts/tts.py) - Accept agent configuration
- [`src/voicebot_app/services/stt/stt.py`](src/voicebot_app/services/stt/stt.py) - Accept agent configuration
- [`src/voicebot_app/services/voicebot_wrapper/voicebot_service.py`](src/voicebot_app/services/voicebot_wrapper/voicebot_service.py) - Agent integration

**Implementation Steps:**
1. Modify service constructors to accept agent_id parameter
2. Update provider initialization to use agent configuration
3. Implement runtime provider switching
4. Add agent context to service methods
5. Test service integration with agent configurations

### Phase 2B: Agent Management API
**Files to create:**
- [`src/voicebot_app/services/agent/routes.py`](src/voicebot_app/services/agent/routes.py) - API endpoints
- [`src/voicebot_app/services/agent/schemas.py`](src/voicebot_app/services/agent/schemas.py) - API schemas
- [`src/voicebot_app/services/agent/dependencies.py`](src/voicebot_app/services/agent/dependencies.py) - FastAPI dependencies

**API Endpoints:**
- `GET /api/agents` - List agents
- `POST /api/agents` - Create agent
- `GET /api/agents/{agent_id}` - Get agent details
- `PUT /api/agents/{agent_id}` - Update agent
- `DELETE /api/agents/{agent_id}` - Delete agent
- `POST /api/agents/{agent_id}/set-default` - Set as default
- `GET /api/agents/current` - Get current agent

**Implementation Steps:**
1. Create FastAPI router for agent management
2. Implement all CRUD endpoints
3. Add validation and error handling
4. Create API documentation
5. Write API tests

### Phase 2C: Runtime Agent Switching
**Files to modify:**
- [`src/voicebot_app/services/agent/agent_manager.py`](src/voicebot_app/services/agent/agent_manager.py) - Add session management
- [`src/voicebot_app/services/agent/routes.py`](src/voicebot_app/services/agent/routes.py) - Add agent selection endpoints

**Implementation Steps:**
1. Implement agent session management
2. Add agent selection endpoints for different interfaces
3. Create agent context middleware
4. Test runtime agent switching
5. Verify session persistence

---

## Phase 3: Interface Updates

### Phase 3A: RAG/Chat Interface Updates
**Files to modify:**
- [`src/voicebot_app/services/rag/chatbot_routes.py`](src/voicebot_app/services/rag/chatbot_routes.py) - Add agent selection
- [`src/voicebot_app/services/rag/templates/chatbot.html`](src/voicebot_app/services/rag/templates/chatbot.html) - Add agent dropdown

**Implementation Steps:**
1. Add agent selection parameter to chatbot routes
2. Update HTML template with agent dropdown
3. Implement JavaScript for agent switching
4. Test agent switching in chat interface
5. Verify conversation continuity

### Phase 3B: Voicebot Interface Updates
**Files to modify:**
- [`src/voicebot_app/services/voicebot_wrapper/routes.py`](src/voicebot_app/services/voicebot_wrapper/routes.py) - Agent integration
- [`src/voicebot_app/services/voicebot_wrapper/templates/voicebot.html`](src/voicebot_app/services/voicebot_wrapper/templates/voicebot.html) - UI updates
- [`src/voicebot_app/services/voicebot_wrapper/static/voicebot.js`](src/voicebot_app/services/voicebot_wrapper/static/voicebot.js) - Client-side logic

**Implementation Steps:**
1. Integrate agent selection in voicebot routes
2. Update voicebot UI with agent controls
3. Implement real-time agent switching
4. Test voicebot with different agents
5. Verify audio streaming continuity

### Phase 3C: TTS/STT Interface Updates
**Files to modify:**
- [`src/voicebot_app/services/tts/web_routes.py`](src/voicebot_app/services/tts/web_routes.py) - Agent support
- [`src/voicebot_app/services/tts/templates/tts_interface.html`](src/voicebot_app/services/tts/templates/tts_interface.html) - UI updates
- [`src/voicebot_app/services/stt/web_routes.py`](src/voicebot_app/services/stt/web_routes.py) - Agent support
- [`src/voicebot_app/services/stt/templates/stt_interface.html`](src/voicebot_app/services/stt/templates/stt_interface.html) - UI updates

**Implementation Steps:**
1. Add agent selection to TTS/STT routes
2. Update interface templates
3. Test agent-specific TTS/STT configurations
4. Verify interface functionality

---

## Phase 4: Admin Interface & Finalization

### Phase 4A: Agent Administration UI
**Files to create:**
- [`src/voicebot_app/services/agent/templates/`](src/voicebot_app/services/agent/templates/) - Admin templates
- [`src/voicebot_app/services/agent/static/`](src/voicebot_app/services/agent/static/) - Admin static files
- [`src/voicebot_app/services/agent/admin_routes.py`](src/voicebot_app/services/agent/admin_routes.py) - Admin endpoints

**Features:**
- Agent list with search and filtering
- Agent creation/editing forms
- Provider configuration forms
- Agent testing functionality
- Default agent management

**Implementation Steps:**
1. Create admin route structure
2. Build agent management UI
3. Implement provider configuration forms
4. Add agent testing functionality
5. Create comprehensive admin interface

### Phase 4B: Testing & Migration
**Files to modify:**
- All existing test files to use default dev agent
- [`src/voicebot_app/.env`](src/voicebot_app/.env) - Update documentation
- Create migration scripts for existing configurations

**Implementation Steps:**
1. Update all existing tests to use agent system
2. Create migration guide for existing deployments
3. Test full system integration
4. Performance testing with multiple agents
5. Security testing and validation

### Phase 4C: Documentation & Deployment
**Files to create:**
- [`documentation/agent_management.md`](documentation/agent_management.md) - User documentation
- [`documentation/agent_api_reference.md`](documentation/agent_api_reference.md) - API reference
- [`documentation/agent_migration_guide.md`](documentation/agent_migration_guide.md) - Migration guide

**Implementation Steps:**
1. Create comprehensive user documentation
2. Write API reference documentation
3. Create migration guide for existing users
4. Update project README with agent features
5. Prepare deployment instructions

---

## Dependencies by Phase

### Phase 1 Dependencies
```txt
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0
pydantic>=2.0.0
```

### Phase 2 Dependencies
```txt
fastapi>=0.100.0  # (already present)
python-multipart>=0.0.6
```

### Phase 3 Dependencies
```txt
# No new dependencies - uses existing frontend stack
```

### Phase 4 Dependencies
```txt
# No new dependencies - uses existing testing and deployment tools
```

## Success Criteria by Phase

### Phase 1 Success
- ✅ PostgreSQL database running with agent tables
- ✅ Alembic migrations working correctly
- ✅ AgentService CRUD operations functional
- ✅ AgentManager caching and resolution working
- ✅ Default dev agent created from .env
- ✅ All unit tests passing

### Phase 2 Success
- ✅ LLM/TTS/STT services accept agent configuration
- ✅ Runtime agent switching working
- ✅ All API endpoints functional
- ✅ Agent sessions properly managed
- ✅ Backward compatibility maintained

### Phase 3 Success
- ✅ All interfaces support agent selection
- ✅ Real-time agent switching working
- ✅ No service interruption during agent changes
- ✅ All existing functionality preserved
- ✅ User experience smooth and intuitive

### Phase 4 Success
- ✅ Admin interface fully functional
- ✅ All tests updated and passing
- ✅ Comprehensive documentation created
- ✅ Performance meets requirements (<100ms switching)
- ✅ System ready for production deployment

This phased approach ensures systematic development with clear milestones and testing at each stage.