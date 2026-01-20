export interface Agent {
  id: string;
  name: string;
  description?: string;
  system_prompt?: string;
  rag_config_id?: string | null;
  llm_provider?: string;
  llm_config?: {
    model?: string;
    api_key?: string;
  };
  tts_provider?: string;
  tts_config?: {
    voice?: string;
    model?: string;
    api_key?: string;
  };
  stt_provider?: string;
  stt_config?: {
    model?: string;
    api_key?: string;
  };
}

export interface AgentResponse {
  agents: Agent[];
  default_agent?: Agent;
}

// Tool-related types
export interface ToolFieldDefinition {
  name: string;
  type: string;
  label: string;
  description?: string;
  required: boolean;
  default?: unknown;
  options?: string[];
}

export interface IntegrationDefinition {
  slug: string;
  name: string;
  description: string;
  fields: ToolFieldDefinition[];
}

export interface ToolDefinition {
  slug: string;
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  integrations: IntegrationDefinition[];
}

export interface AvailableToolsResponse {
  tools: ToolDefinition[];
}

export interface AgentTool {
  id: string;
  agent_id: string;
  tool_slug: string;
  integration_slug: string;
  integration_config: Record<string, string>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}
