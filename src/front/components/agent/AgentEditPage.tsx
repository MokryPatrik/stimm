'use client';

import { useState, useEffect, useCallback } from 'react';
import { PageLayout } from '@/components/ui/PageLayout';
import { PageCard } from '@/components/ui/PageCard';
import { ModalWrapper } from '@/components/ui/ModalWrapper';
import { useModalRouter } from '@/hooks/use-modal-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Agent,
  AgentTool,
  AvailableToolsResponse,
  ToolDefinition,
} from './types';
import { THEME } from '@/lib/theme';
import { Bot, Database, ArrowLeft, Save, Wrench, Plus, Trash2, ToggleLeft, ToggleRight, Settings, X, Check, RefreshCw } from 'lucide-react';
import { config } from '@/lib/frontend-config';

const API_URL = config.browser.stimmApiUrl;

interface ProviderConfig {
  providers: { value: string; label: string }[];
  configurable_fields: Record<
    string,
    Record<string, { type: string; label: string; required: boolean }>
  >;
}

interface AvailableProviders {
  llm: ProviderConfig;
  tts: ProviderConfig;
  stt: ProviderConfig;
}

interface ProviderFields {
  [key: string]: { type: string; label: string; required: boolean };
}

interface AgentEditPageProps {
  agentId?: string;
}

export function AgentEditPage({ agentId }: AgentEditPageProps) {
  const { isModalMode, closeModal } = useModalRouter();

  const [agent, setAgent] = useState<Partial<Agent>>({
    name: '',
    description: '',
    system_prompt: '',
    llm_provider: '',
    tts_provider: '',
    stt_provider: '',
    rag_config_id: null,
    llm_config: {},
    tts_config: {},
    stt_config: {},
  });
  const [providers, setProviders] = useState<AvailableProviders | null>(null);
  const [ragConfigs, setRagConfigs] = useState<{ id: string; name: string }[]>(
    []
  );
  const [providerFields, setProviderFields] = useState<
    Record<string, ProviderFields>
  >({
    llm: {},
    tts: {},
    stt: {},
  });
  const [loading, setLoading] = useState(!!agentId);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Tools state
  const [availableTools, setAvailableTools] = useState<ToolDefinition[]>([]);
  const [agentTools, setAgentTools] = useState<AgentTool[]>([]);
  const [showAddTool, setShowAddTool] = useState(false);
  const [newToolSlug, setNewToolSlug] = useState('');
  const [newIntegrationSlug, setNewIntegrationSlug] = useState('');
  const [newToolConfig, setNewToolConfig] = useState<Record<string, string>>({});
  const [addingTool, setAddingTool] = useState(false);
  
  // Tool editing state
  const [editingToolSlug, setEditingToolSlug] = useState<string | null>(null);
  const [editToolConfig, setEditToolConfig] = useState<Record<string, string>>({});
  const [savingToolConfig, setSavingToolConfig] = useState(false);

  // RAG sync state
  const [syncStatus, setSyncStatus] = useState<Record<string, {
    rag_sync_enabled: boolean;
    last_sync_at: string | null;
    last_sync_count: number;
    sync_interval_hours: number;
    next_sync_at: string | null;
  }>>({});
  const [syncingTools, setSyncingTools] = useState<Set<string>>(new Set());

  const loadProviders = useCallback(async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/agents/providers/available`
      );
      if (!response.ok) {
        throw new Error(`Failed to load providers: ${response.statusText}`);
      }
      const providerData = await response.json();
      setProviders(providerData);
    } catch (err) {
      console.error('Failed to load providers:', err);
    }
  }, []);

  const loadRagConfigs = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/rag-configs/`);
      if (!response.ok) {
        throw new Error(`Failed to load RAG configs: ${response.statusText}`);
      }
      const data = await response.json();
      setRagConfigs(
        data.map((config: any) => ({ id: config.id, name: config.name }))
      );
    } catch (err) {
      console.error('Failed to load RAG configs:', err);
    }
  }, []);

  const loadAgent = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_URL}/api/agents/${agentId}`
      );
      if (!response.ok) {
        throw new Error(`Failed to load agent: ${response.statusText}`);
      }

      const agentData = await response.json();
      setAgent(agentData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const loadProviderFields = useCallback(
    async (providerType: string, providerName: string) => {
      try {
        const response = await fetch(
          `${API_URL}/api/agents/providers/${providerType}/${providerName}/fields`
        );
        if (!response.ok) {
          throw new Error(
            `Failed to load provider fields: ${response.statusText}`
          );
        }
        const fields = await response.json();

        setProviderFields((prev) => ({
          ...prev,
          [providerType]: fields,
        }));
      } catch (err) {
        console.error(
          `Failed to load fields for ${providerType}.${providerName}:`,
          err
        );
      }
    },
    []
  );

  // Load available tools catalog
  const loadAvailableTools = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/tools/available`);
      if (!response.ok) {
        throw new Error(`Failed to load available tools: ${response.statusText}`);
      }
      const data: AvailableToolsResponse = await response.json();
      setAvailableTools(data.tools);
    } catch (err) {
      console.error('Failed to load available tools:', err);
    }
  }, []);

  // Load agent's configured tools
  const loadAgentTools = useCallback(async () => {
    if (!agentId) return;
    try {
      const response = await fetch(`${API_URL}/api/agents/${agentId}/tools`);
      if (!response.ok) {
        throw new Error(`Failed to load agent tools: ${response.statusText}`);
      }
      const data: AgentTool[] = await response.json();
      setAgentTools(data);
      
      // Load sync status for each tool
      for (const tool of data) {
        loadToolSyncStatus(tool.tool_slug);
      }
    } catch (err) {
      console.error('Failed to load agent tools:', err);
    }
  }, [agentId]);

  // Load sync status for a specific tool
  const loadToolSyncStatus = useCallback(async (toolSlug: string) => {
    if (!agentId) return;
    try {
      const response = await fetch(
        `${API_URL}/api/agents/${agentId}/tools/${toolSlug}/sync/status`
      );
      if (!response.ok) return;
      
      const data = await response.json();
      setSyncStatus((prev) => ({
        ...prev,
        [toolSlug]: data,
      }));
    } catch (err) {
      console.error(`Failed to load sync status for ${toolSlug}:`, err);
    }
  }, [agentId]);

  // Trigger sync for a tool
  const handleTriggerSync = async (toolSlug: string) => {
    if (!agentId) return;
    
    try {
      setSyncingTools((prev) => new Set(prev).add(toolSlug));
      
      const response = await fetch(
        `${API_URL}/api/agents/${agentId}/tools/${toolSlug}/sync?force=true`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to trigger sync');
      }
      
      // Poll for sync completion
      const pollStatus = async () => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await loadToolSyncStatus(toolSlug);
        await loadAgentTools(); // Refresh to get updated config
      };
      
      // Start polling
      pollStatus();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger sync');
    } finally {
      setSyncingTools((prev) => {
        const newSet = new Set(prev);
        newSet.delete(toolSlug);
        return newSet;
      });
    }
  };

  // Add tool to agent
  const handleAddTool = async () => {
    if (!agentId || !newToolSlug || !newIntegrationSlug) return;
    
    try {
      setAddingTool(true);
      const response = await fetch(`${API_URL}/api/agents/${agentId}/tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_slug: newToolSlug,
          integration_slug: newIntegrationSlug,
          integration_config: newToolConfig,
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to add tool: ${errorText}`);
      }
      
      // Reset form and reload tools
      setNewToolSlug('');
      setNewIntegrationSlug('');
      setNewToolConfig({});
      setShowAddTool(false);
      await loadAgentTools();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add tool');
    } finally {
      setAddingTool(false);
    }
  };

  // Remove tool from agent
  const handleRemoveTool = async (toolSlug: string) => {
    if (!agentId) return;
    
    try {
      const response = await fetch(
        `${API_URL}/api/agents/${agentId}/tools/${toolSlug}`,
        { method: 'DELETE' }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to remove tool: ${response.statusText}`);
      }
      
      await loadAgentTools();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove tool');
    }
  };

  // Toggle tool enabled/disabled
  const handleToggleTool = async (toolSlug: string, currentEnabled: boolean) => {
    if (!agentId) return;
    
    try {
      const endpoint = currentEnabled ? 'disable' : 'enable';
      const response = await fetch(
        `${API_URL}/api/agents/${agentId}/tools/${toolSlug}/${endpoint}`,
        { method: 'PUT' }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to toggle tool: ${response.statusText}`);
      }
      
      await loadAgentTools();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle tool');
    }
  };

  // Start editing a tool's configuration
  const handleStartEditTool = (tool: AgentTool) => {
    setEditingToolSlug(tool.tool_slug);
    setEditToolConfig({ ...tool.integration_config });
  };

  // Cancel editing
  const handleCancelEditTool = () => {
    setEditingToolSlug(null);
    setEditToolConfig({});
  };

  // Save tool configuration
  const handleSaveToolConfig = async (toolSlug: string) => {
    if (!agentId) return;
    
    try {
      setSavingToolConfig(true);
      const response = await fetch(
        `${API_URL}/api/agents/${agentId}/tools/${toolSlug}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            integration_config: editToolConfig,
          }),
        }
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to update tool config: ${errorText}`);
      }
      
      setEditingToolSlug(null);
      setEditToolConfig({});
      await loadAgentTools();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save tool config');
    } finally {
      setSavingToolConfig(false);
    }
  };

  // Get selected tool definition
  const selectedTool = availableTools.find((t) => t.slug === newToolSlug);
  const selectedIntegration = selectedTool?.integrations.find(
    (i) => i.slug === newIntegrationSlug
  );

  useEffect(() => {
    loadProviders();
    loadRagConfigs();
    loadAvailableTools();
    if (agentId) {
      loadAgent();
      loadAgentTools();
    }
  }, [agentId, loadProviders, loadRagConfigs, loadAgent, loadAvailableTools, loadAgentTools]);

  useEffect(() => {
    if (agent && providers) {
      const loadExistingProviderFields = async () => {
        if (agent.llm_provider) {
          await loadProviderFields('llm', agent.llm_provider);
        }
        if (agent.tts_provider) {
          await loadProviderFields('tts', agent.tts_provider);
        }
        if (agent.stt_provider) {
          await loadProviderFields('stt', agent.stt_provider);
        }
      };

      loadExistingProviderFields();
    }
  }, [agent, providers, loadProviderFields]);

  const handleProviderChange = async (
    providerType: string,
    providerName: string
  ) => {
    handleInputChange(`${providerType}_provider`, providerName);

    if (providerName) {
      await loadProviderFields(providerType, providerName);

      const configFields = providerFields[providerType];
      const newConfig: Record<string, string> = {};

      // Validate field names before using them
      Object.keys(configFields).forEach((field) => {
        if (typeof field === 'string' && field.length > 0) {
          newConfig[field] = '';
        }
      });

      handleInputChange(`${providerType}_config`, newConfig);
    } else {
      handleInputChange(`${providerType}_config`, {});
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const payload = {
        name: agent.name || '',
        description: agent.description || '',
        system_prompt: agent.system_prompt || '',
        rag_config_id:
          agent.rag_config_id === '' || agent.rag_config_id === 'none'
            ? null
            : agent.rag_config_id || null,
        llm_config: agent.llm_provider
          ? {
              provider: agent.llm_provider,
              config: (agent.llm_config as Record<string, string>) || {},
            }
          : undefined,
        tts_config: agent.tts_provider
          ? {
              provider: agent.tts_provider,
              config: (agent.tts_config as Record<string, string>) || {},
            }
          : undefined,
        stt_config: agent.stt_provider
          ? {
              provider: agent.stt_provider,
              config: (agent.stt_config as Record<string, string>) || {},
            }
          : undefined,
      };

      const url = agentId
        ? `${API_URL}/api/agents/${agentId}`
        : `${API_URL}/api/agents/`;

      const method = agentId ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to save agent: ${response.statusText} - ${errorText}`
        );
      }

      if (isModalMode) {
        closeModal();
      } else {
        window.location.href = '/agent/admin';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field: string, value: string | object | null) => {
    setAgent((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleConfigChange = (
    configField: string,
    field: string,
    value: string
  ) => {
    // Validate field name to prevent object injection
    if (typeof field !== 'string' || field.length === 0) {
      console.warn('Invalid field name in handleConfigChange:', field);
      return;
    }

    setAgent((prev) => ({
      ...prev,
      [configField]: {
        ...((prev[configField as keyof Agent] as object) || {}),
        [field]: value,
      },
    }));
  };

  const content = (
    <>
      {error && (
        <Alert
          variant="destructive"
          className="mb-6 bg-red-900/50 border-red-500/50"
        >
          <AlertDescription className="text-white">{error}</AlertDescription>
        </Alert>
      )}

      <PageCard>
        <div className="space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <h3
              className={`text-lg font-semibold ${THEME.text.accent} flex items-center gap-2`}
            >
              <Bot className="w-5 h-5" />
              Basic Information
            </h3>

            <div>
              <Label htmlFor="name" className={THEME.text.secondary}>
                Agent Name *
              </Label>
              <Input
                id="name"
                value={agent.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Enter agent name"
                className={`${THEME.input.base} mt-1`}
              />
            </div>

            <div>
              <Label htmlFor="description" className={THEME.text.secondary}>
                Description
              </Label>
              <Input
                id="description"
                value={agent.description || ''}
                onChange={(e) =>
                  handleInputChange('description', e.target.value)
                }
                placeholder="Enter agent description"
                className={`${THEME.input.base} mt-1`}
              />
            </div>

            <div>
              <Label htmlFor="system_prompt" className={THEME.text.secondary}>
                System Prompt
              </Label>
              <textarea
                id="system_prompt"
                value={agent.system_prompt || ''}
                onChange={(e) =>
                  handleInputChange('system_prompt', e.target.value)
                }
                placeholder="Enter system prompt for the agent (optional)"
                className={`${THEME.input.base} w-full min-h-[120px] p-3 rounded-md mt-1 resize-none`}
              />
            </div>
          </div>

          {/* LLM Configuration */}
          <div className="space-y-4 pt-6 border-t border-white/10">
            <h3 className={`text-lg font-semibold ${THEME.text.accent}`}>
              LLM Provider
            </h3>

            <div>
              <Label htmlFor="llm_provider" className={THEME.text.secondary}>
                Provider
              </Label>
              <Select
                value={agent.llm_provider || ''}
                onValueChange={(value) => handleProviderChange('llm', value)}
              >
                <SelectTrigger
                  id="llm_provider"
                  className={`${THEME.input.select} mt-1`}
                >
                  <SelectValue placeholder="Select LLM Provider" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-white/20">
                  {providers?.llm.providers.map((provider) => (
                    <SelectItem
                      key={provider.value}
                      value={provider.value}
                      className="text-white"
                    >
                      {provider.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {agent.llm_provider && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4 border-l-2 border-cyan-500/30">
                {Object.entries(providerFields.llm).map(([field, fieldDef]) => (
                  <div key={field}>
                    <Label
                      htmlFor={`llm_${field}`}
                      className={THEME.text.secondary}
                    >
                      {fieldDef.label}
                    </Label>
                    <Input
                      id={`llm_${field}`}
                      type={fieldDef.type === 'password' ? 'password' : 'text'}
                      value={
                        typeof field === 'string' &&
                        agent.llm_config &&
                        (agent.llm_config as Record<string, string>)[field]
                          ? (agent.llm_config as Record<string, string>)[field]
                          : ''
                      }
                      onChange={(e) =>
                        handleConfigChange('llm_config', field, e.target.value)
                      }
                      placeholder={`Enter ${fieldDef.label}`}
                      className={`${THEME.input.base} mt-1`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* TTS Configuration */}
          <div className="space-y-4 pt-6 border-t border-white/10">
            <h3 className={`text-lg font-semibold ${THEME.text.accent}`}>
              TTS Provider
            </h3>

            <div>
              <Label htmlFor="tts_provider" className={THEME.text.secondary}>
                Provider
              </Label>
              <Select
                value={agent.tts_provider || ''}
                onValueChange={(value) => handleProviderChange('tts', value)}
              >
                <SelectTrigger
                  id="tts_provider"
                  className={`${THEME.input.select} mt-1`}
                >
                  <SelectValue placeholder="Select TTS Provider" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-white/20">
                  {providers?.tts.providers.map((provider) => (
                    <SelectItem
                      key={provider.value}
                      value={provider.value}
                      className="text-white"
                    >
                      {provider.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {agent.tts_provider && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4 border-l-2 border-purple-500/30">
                {Object.entries(providerFields.tts).map(([field, fieldDef]) => (
                  <div key={field}>
                    <Label
                      htmlFor={`tts_${field}`}
                      className={THEME.text.secondary}
                    >
                      {fieldDef.label}
                    </Label>
                    <Input
                      id={`tts_${field}`}
                      type={fieldDef.type === 'password' ? 'password' : 'text'}
                      value={
                        typeof field === 'string' &&
                        agent.tts_config &&
                        (agent.tts_config as Record<string, string>)[field]
                          ? (agent.tts_config as Record<string, string>)[field]
                          : ''
                      }
                      onChange={(e) =>
                        handleConfigChange('tts_config', field, e.target.value)
                      }
                      placeholder={`Enter ${fieldDef.label}`}
                      className={`${THEME.input.base} mt-1`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* STT Configuration */}
          <div className="space-y-4 pt-6 border-t border-white/10">
            <h3 className={`text-lg font-semibold ${THEME.text.accent}`}>
              STT Provider
            </h3>

            <div>
              <Label htmlFor="stt_provider" className={THEME.text.secondary}>
                Provider
              </Label>
              <Select
                value={agent.stt_provider || ''}
                onValueChange={(value) => handleProviderChange('stt', value)}
              >
                <SelectTrigger
                  id="stt_provider"
                  className={`${THEME.input.select} mt-1`}
                >
                  <SelectValue placeholder="Select STT Provider" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-white/20">
                  {providers?.stt.providers.map((provider) => (
                    <SelectItem
                      key={provider.value}
                      value={provider.value}
                      className="text-white"
                    >
                      {provider.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {agent.stt_provider && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4 border-l-2 border-orange-500/30">
                {Object.entries(providerFields.stt).map(([field, fieldDef]) => (
                  <div key={field}>
                    <Label
                      htmlFor={`stt_${field}`}
                      className={THEME.text.secondary}
                    >
                      {fieldDef.label}
                    </Label>
                    <Input
                      id={`stt_${field}`}
                      type={fieldDef.type === 'password' ? 'password' : 'text'}
                      value={
                        typeof field === 'string' &&
                        agent.stt_config &&
                        (agent.stt_config as Record<string, string>)[field]
                          ? (agent.stt_config as Record<string, string>)[field]
                          : ''
                      }
                      onChange={(e) =>
                        handleConfigChange('stt_config', field, e.target.value)
                      }
                      placeholder={`Enter ${fieldDef.label}`}
                      className={`${THEME.input.base} mt-1`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* RAG Configuration */}
          <div className="space-y-4 pt-6 border-t border-white/10">
            <h3
              className={`text-lg font-semibold ${THEME.text.accent} flex items-center gap-2`}
            >
              <Database className="w-5 h-5" />
              RAG Configuration
            </h3>

            <div>
              <Label htmlFor="rag_config_id" className={THEME.text.secondary}>
                RAG Configuration (Optional)
              </Label>
              <Select
                value={
                  agent.rag_config_id === null || agent.rag_config_id === ''
                    ? 'none'
                    : agent.rag_config_id
                }
                onValueChange={(value) =>
                  handleInputChange(
                    'rag_config_id',
                    value === 'none' ? null : value
                  )
                }
              >
                <SelectTrigger
                  id="rag_config_id"
                  className={`${THEME.input.select} mt-1`}
                >
                  <SelectValue placeholder="Select RAG Configuration (optional)" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-white/20">
                  <SelectItem value="none" className="text-white">
                    None
                  </SelectItem>
                  {ragConfigs.map((config) => (
                    <SelectItem
                      key={config.id}
                      value={config.id}
                      className="text-white"
                    >
                      {config.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="mt-2 text-sm">
                <a
                  href="/rag/admin"
                  className={`${THEME.text.accent} hover:underline`}
                >
                  → Manage RAG configurations
                </a>
              </div>
            </div>
          </div>

          {/* Tools Configuration - Only show for existing agents */}
          {agentId && (
            <div className="space-y-4 pt-6 border-t border-white/10">
              <div className="flex items-center justify-between">
                <h3
                  className={`text-lg font-semibold ${THEME.text.accent} flex items-center gap-2`}
                >
                  <Wrench className="w-5 h-5" />
                  Tools / Function Calling
                </h3>
                <Button
                  onClick={() => setShowAddTool(!showAddTool)}
                  className={`${THEME.button.ghost} rounded-full px-4 py-2 flex items-center gap-2`}
                >
                  <Plus className="w-4 h-4" />
                  Add Tool
                </Button>
              </div>

              <p className={`text-sm ${THEME.text.muted}`}>
                Enable tools to allow your agent to perform actions like searching products,
                looking up orders, or calling external APIs.
              </p>

              {/* Add Tool Form */}
              {showAddTool && (
                <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-4">
                  <h4 className={`font-medium ${THEME.text.primary}`}>Add New Tool</h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label className={THEME.text.secondary}>Tool</Label>
                      <Select
                        value={newToolSlug}
                        onValueChange={(value) => {
                          setNewToolSlug(value);
                          setNewIntegrationSlug('');
                          setNewToolConfig({});
                        }}
                      >
                        <SelectTrigger className={`${THEME.input.select} mt-1`}>
                          <SelectValue placeholder="Select a tool" />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-900 border-white/20">
                          {availableTools
                            .filter((t) => !agentTools.some((at) => at.tool_slug === t.slug))
                            .map((tool) => (
                              <SelectItem key={tool.slug} value={tool.slug} className="text-white">
                                {tool.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      {selectedTool && (
                        <p className={`text-xs ${THEME.text.muted} mt-1`}>
                          {selectedTool.description}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label className={THEME.text.secondary}>Integration</Label>
                      <Select
                        value={newIntegrationSlug}
                        onValueChange={(value) => {
                          setNewIntegrationSlug(value);
                          setNewToolConfig({});
                        }}
                        disabled={!newToolSlug}
                      >
                        <SelectTrigger className={`${THEME.input.select} mt-1`}>
                          <SelectValue placeholder="Select an integration" />
                        </SelectTrigger>
                        <SelectContent className="bg-gray-900 border-white/20">
                          {selectedTool?.integrations.map((integration) => (
                            <SelectItem
                              key={integration.slug}
                              value={integration.slug}
                              className="text-white"
                            >
                              {integration.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Integration config fields */}
                  {selectedIntegration && selectedIntegration.fields.length > 0 && (
                    <div className="space-y-3 pl-4 border-l-2 border-green-500/30">
                      <p className={`text-sm ${THEME.text.secondary}`}>
                        Configuration for {selectedIntegration.name}:
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {selectedIntegration.fields.map((field) => (
                          <div key={field.name}>
                            <Label className={THEME.text.secondary}>
                              {field.label}
                              {field.required && <span className="text-red-400 ml-1">*</span>}
                            </Label>
                            <Input
                              type={field.type === 'password' ? 'password' : 'text'}
                              value={newToolConfig[field.name] || ''}
                              onChange={(e) =>
                                setNewToolConfig((prev) => ({
                                  ...prev,
                                  [field.name]: e.target.value,
                                }))
                              }
                              placeholder={field.description || `Enter ${field.label}`}
                              className={`${THEME.input.base} mt-1`}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      onClick={handleAddTool}
                      disabled={addingTool || !newToolSlug || !newIntegrationSlug}
                      className={`${THEME.button.secondary} rounded-full px-4`}
                    >
                      {addingTool ? 'Adding...' : 'Add Tool'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowAddTool(false);
                        setNewToolSlug('');
                        setNewIntegrationSlug('');
                        setNewToolConfig({});
                      }}
                      className={`${THEME.button.ghost} rounded-full px-4`}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Configured Tools List */}
              {agentTools.length > 0 ? (
                <div className="space-y-2">
                  {agentTools.map((tool) => {
                    const toolDef = availableTools.find((t) => t.slug === tool.tool_slug);
                    const integrationDef = toolDef?.integrations.find(
                      (i) => i.slug === tool.integration_slug
                    );
                    const isEditing = editingToolSlug === tool.tool_slug;
                    
                    return (
                      <div
                        key={tool.id}
                        className={`p-4 rounded-lg border ${
                          tool.is_enabled
                            ? 'bg-green-500/10 border-green-500/30'
                            : 'bg-gray-500/10 border-gray-500/30'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Wrench
                              className={`w-5 h-5 ${
                                tool.is_enabled ? 'text-green-400' : 'text-gray-400'
                              }`}
                            />
                            <div>
                              <p className={`font-medium ${THEME.text.primary}`}>
                                {toolDef?.name || tool.tool_slug}
                              </p>
                              <p className={`text-sm ${THEME.text.muted}`}>
                                Integration: {integrationDef?.name || tool.integration_slug}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleStartEditTool(tool)}
                              className="p-2 text-blue-400 hover:bg-blue-400/10"
                              title="Configure tool"
                            >
                              <Settings className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleTool(tool.tool_slug, tool.is_enabled)}
                              className={`p-2 ${
                                tool.is_enabled ? 'text-green-400' : 'text-gray-400'
                              } hover:bg-white/10`}
                              title={tool.is_enabled ? 'Disable tool' : 'Enable tool'}
                            >
                              {tool.is_enabled ? (
                                <ToggleRight className="w-5 h-5" />
                              ) : (
                                <ToggleLeft className="w-5 h-5" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveTool(tool.tool_slug)}
                              className="p-2 text-red-400 hover:bg-red-400/10"
                              title="Remove tool"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>

                        {/* Edit Configuration Form */}
                        {isEditing && integrationDef && (
                          <div className="mt-4 pt-4 border-t border-white/10 space-y-4">
                            <h4 className={`text-sm font-medium ${THEME.text.secondary}`}>
                              Configuration for {integrationDef.name}
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {integrationDef.fields.map((field) => (
                                <div key={field.name}>
                                  <Label
                                    htmlFor={`edit-${field.name}`}
                                    className={`${THEME.text.secondary} text-sm`}
                                  >
                                    {field.label}
                                    {field.required && (
                                      <span className="text-red-400 ml-1">*</span>
                                    )}
                                  </Label>
                                  <Input
                                    id={`edit-${field.name}`}
                                    type={field.type === 'password' ? 'password' : 'text'}
                                    value={editToolConfig[field.name] || ''}
                                    onChange={(e) =>
                                      setEditToolConfig((prev) => ({
                                        ...prev,
                                        [field.name]: e.target.value,
                                      }))
                                    }
                                    placeholder={field.description || `Enter ${field.label}`}
                                    className={`${THEME.input.base} mt-1`}
                                  />
                                </div>
                              ))}
                            </div>
                            <div className="flex gap-2">
                              <Button
                                onClick={() => handleSaveToolConfig(tool.tool_slug)}
                                disabled={savingToolConfig}
                                className={`${THEME.button.secondary} rounded-full px-4 flex items-center gap-2`}
                              >
                                <Check className="w-4 h-4" />
                                {savingToolConfig ? 'Saving...' : 'Save Config'}
                              </Button>
                              <Button
                                variant="outline"
                                onClick={handleCancelEditTool}
                                className={`${THEME.button.ghost} rounded-full px-4 flex items-center gap-2`}
                              >
                                <X className="w-4 h-4" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* RAG Sync Status - Show for product_search tool when use_as_rag is enabled */}
                        {tool.tool_slug === 'product_search' && 
                         tool.integration_config?.use_as_rag && (
                          <div className="mt-4 pt-4 border-t border-white/10">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className={`text-sm font-medium ${THEME.text.secondary}`}>
                                  RAG Sync Status
                                </p>
                                {syncStatus[tool.tool_slug]?.last_sync_at ? (
                                  <div className={`text-xs ${THEME.text.muted} mt-1`}>
                                    <p>
                                      Last sync: {new Date(syncStatus[tool.tool_slug].last_sync_at!).toLocaleString()}
                                    </p>
                                    <p>
                                      Products synced: {syncStatus[tool.tool_slug].last_sync_count}
                                    </p>
                                    {syncStatus[tool.tool_slug].next_sync_at && (
                                      <p>
                                        Next auto-sync: {new Date(syncStatus[tool.tool_slug].next_sync_at!).toLocaleString()}
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <p className={`text-xs ${THEME.text.muted} mt-1`}>
                                    Never synced - click Sync Now to import products to RAG
                                  </p>
                                )}
                              </div>
                              <Button
                                onClick={() => handleTriggerSync(tool.tool_slug)}
                                disabled={syncingTools.has(tool.tool_slug)}
                                className={`${THEME.button.ghost} rounded-full px-4 flex items-center gap-2`}
                              >
                                <RefreshCw 
                                  className={`w-4 h-4 ${
                                    syncingTools.has(tool.tool_slug) ? 'animate-spin' : ''
                                  }`} 
                                />
                                {syncingTools.has(tool.tool_slug) ? 'Syncing...' : 'Sync Now'}
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className={`text-center py-8 ${THEME.text.muted}`}>
                  <Wrench className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No tools configured for this agent yet.</p>
                  <p className="text-sm mt-1">
                    Click &quot;Add Tool&quot; to enable function calling capabilities.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Tools notice for new agents */}
          {!agentId && (
            <div className="space-y-4 pt-6 border-t border-white/10">
              <h3
                className={`text-lg font-semibold ${THEME.text.muted} flex items-center gap-2`}
              >
                <Wrench className="w-5 h-5" />
                Tools / Function Calling
              </h3>
              <p className={`text-sm ${THEME.text.muted}`}>
                Save the agent first, then you can configure tools for function calling.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 pt-6 border-t border-white/10">
            <Button
              onClick={handleSave}
              disabled={saving}
              className={`${THEME.button.secondary} rounded-full px-6 flex items-center gap-2`}
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Agent'}
            </Button>

            <Button
              variant="outline"
              onClick={() => {
                if (isModalMode) {
                  closeModal();
                } else {
                  window.location.href = '/agent/admin';
                }
              }}
              className={`${THEME.button.ghost} rounded-full px-6 flex items-center gap-2`}
            >
              <ArrowLeft className="w-4 h-4" />
              Cancel
            </Button>
          </div>
        </div>
      </PageCard>
    </>
  );

  if (loading) {
    return (
      <PageLayout
        title={agentId ? 'Edit Agent' : 'Create Agent'}
        icon={<Bot className="w-8 h-8" />}
      >
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
            <p className={THEME.text.secondary}>Loading agent...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  if (isModalMode) {
    return (
      <ModalWrapper
        isOpen={true}
        onClose={closeModal}
        title={agentId ? 'Edit Agent' : 'Create Agent'}
      >
        {content}
      </ModalWrapper>
    );
  }

  return (
    <PageLayout
      title={agentId ? 'Edit Agent' : 'Create Agent'}
      icon={<Bot className="w-8 h-8" />}
      breadcrumbs={[
        { label: 'Agents', href: '/agent/admin' },
        { label: agentId ? 'Edit' : 'Create', href: '#' },
      ]}
    >
      {content}
    </PageLayout>
  );
}
