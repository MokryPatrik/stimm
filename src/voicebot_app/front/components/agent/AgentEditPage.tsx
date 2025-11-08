'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Agent } from './types'

interface AgentEditPageProps {
  agentId?: string
}

export function AgentEditPage({ agentId }: AgentEditPageProps) {
  const [agent, setAgent] = useState<Partial<Agent>>({
    name: '',
    description: '',
    llm_provider: '',
    tts_provider: '',
    stt_provider: '',
    llm_config: {},
    tts_config: {},
    stt_config: {}
  })
  const [loading, setLoading] = useState(!!agentId)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (agentId) {
      loadAgent()
    }
  }, [agentId])


  const loadAgent = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`http://localhost:8001/api/agents/${agentId}`)
      if (!response.ok) {
        throw new Error(`Failed to load agent: ${response.statusText}`)
      }
      
      const agentData = await response.json()
      setAgent(agentData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)

      const url = agentId 
        ? `http://localhost:8001/api/agents/${agentId}/`
        : 'http://localhost:8001/api/agents/'
      
      const method = agentId ? 'PUT' : 'POST'
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agent),
      })

      if (!response.ok) {
        throw new Error(`Failed to save agent: ${response.statusText}`)
      }

      // Redirect back to admin page after successful save
      window.location.href = '/agent/admin'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent')
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (field: string, value: string | object) => {
    setAgent(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleConfigChange = (configField: string, field: string, value: string) => {
    setAgent(prev => ({
      ...prev,
      [configField]: {
        ...(prev[configField as keyof Agent] as object || {}),
        [field]: value
      }
    }))
  }

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading agent...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader>
          <CardTitle>
            {agentId ? 'Edit Agent' : 'Create New Agent'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Agent Name</Label>
              <Input
                id="name"
                value={agent.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Enter agent name"
              />
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={agent.description || ''}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Enter agent description"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="llm_provider">LLM Provider</Label>
                <Input
                  id="llm_provider"
                  value={agent.llm_provider || ''}
                  onChange={(e) => handleInputChange('llm_provider', e.target.value)}
                  placeholder="e.g., groq.com"
                />
              </div>

              <div>
                <Label htmlFor="tts_provider">TTS Provider</Label>
                <Input
                  id="tts_provider"
                  value={agent.tts_provider || ''}
                  onChange={(e) => handleInputChange('tts_provider', e.target.value)}
                  placeholder="e.g., elevenlabs.io"
                />
              </div>

              <div>
                <Label htmlFor="stt_provider">STT Provider</Label>
                <Input
                  id="stt_provider"
                  value={agent.stt_provider || ''}
                  onChange={(e) => handleInputChange('stt_provider', e.target.value)}
                  placeholder="e.g., whisper.local"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="llm_model">LLM Model</Label>
                <Input
                  id="llm_model"
                  value={agent.llm_config?.model || ''}
                  onChange={(e) => handleConfigChange('llm_config', 'model', e.target.value)}
                  placeholder="e.g., llama-3.1-8b-instant"
                />
              </div>

              <div>
                <Label htmlFor="tts_voice">TTS Voice</Label>
                <Input
                  id="tts_voice"
                  value={agent.tts_config?.voice || ''}
                  onChange={(e) => handleConfigChange('tts_config', 'voice', e.target.value)}
                  placeholder="e.g., EXAVITQu4vr4xnSDxMaL"
                />
              </div>

              <div>
                <Label htmlFor="tts_model">TTS Model ID</Label>
                <Input
                  id="tts_model"
                  value={agent.tts_config?.model_id || ''}
                  onChange={(e) => handleConfigChange('tts_config', 'model_id', e.target.value)}
                  placeholder="e.g., eleven_multilingual_v2"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="llm_api_key">LLM API Key</Label>
                <Input
                  id="llm_api_key"
                  type="password"
                  value={agent.llm_config?.api_key || ''}
                  onChange={(e) => handleConfigChange('llm_config', 'api_key', e.target.value)}
                  placeholder="Enter LLM API key"
                />
              </div>

              <div>
                <Label htmlFor="tts_api_key">TTS API Key</Label>
                <Input
                  id="tts_api_key"
                  type="password"
                  value={agent.tts_config?.api_key || ''}
                  onChange={(e) => handleConfigChange('tts_config', 'api_key', e.target.value)}
                  placeholder="Enter TTS API key"
                />
              </div>

              <div>
                <Label htmlFor="stt_api_key">STT API Key</Label>
                <Input
                  id="stt_api_key"
                  type="password"
                  value={agent.stt_config?.api_key || ''}
                  onChange={(e) => handleConfigChange('stt_config', 'api_key', e.target.value)}
                  placeholder="Enter STT API key"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-4">
            <Button 
              onClick={handleSave} 
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Agent'}
            </Button>
            <Button variant="outline" asChild>
              <a href="/agent/admin">Cancel</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}