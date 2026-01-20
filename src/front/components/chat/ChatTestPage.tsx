'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { PageLayout } from '@/components/ui/PageLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Agent } from '@/components/agent/types';
import { THEME } from '@/lib/theme';
import {
  MessageSquare,
  Send,
  Bot,
  User,
  Loader2,
  Trash2,
  Wrench,
  AlertCircle,
} from 'lucide-react';
import { config } from '@/lib/frontend-config';

const API_URL = config.browser.stimmApiUrl;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: Date;
  toolName?: string;
  isStreaming?: boolean;
}

export function ChatTestPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load agents on mount
  useEffect(() => {
    loadAgents();
  }, []);

  // Update current agent when selection changes
  useEffect(() => {
    if (selectedAgentId && agents.length > 0) {
      const agent = agents.find((a) => a.id === selectedAgentId);
      setCurrentAgent(agent || null);
    }
  }, [selectedAgentId, agents]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/api/agents/`);
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
        // Select first agent by default
        if (data.length > 0 && !selectedAgentId) {
          setSelectedAgentId(data[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load agents:', err);
      setError('Failed to load agents');
    }
  };

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading || !selectedAgentId) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    // Create placeholder for assistant response
    const assistantMessageId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      },
    ]);

    try {
      const response = await fetch(`${API_URL}/rag/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          agent_id: selectedAgentId,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'chunk' && data.content) {
                fullContent += data.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: fullContent }
                      : msg
                  )
                );
              } else if (data.type === 'tool_start') {
                // Add tool execution message
                const toolMessage: ChatMessage = {
                  id: crypto.randomUUID(),
                  role: 'tool',
                  content: `Calling tool...`,
                  toolName: data.tool_name,
                  timestamp: new Date(),
                };
                setMessages((prev) => {
                  // Insert before the assistant message
                  const assistantIndex = prev.findIndex(
                    (m) => m.id === assistantMessageId
                  );
                  if (assistantIndex > 0) {
                    const newMessages = [...prev];
                    newMessages.splice(assistantIndex, 0, toolMessage);
                    return newMessages;
                  }
                  return [...prev, toolMessage];
                });
              } else if (data.type === 'tool_result') {
                // Update tool message with result
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.role === 'tool' && msg.toolName === data.tool_name
                      ? { ...msg, content: data.content || 'Tool executed' }
                      : msg
                  )
                );
              } else if (data.type === 'complete') {
                if (data.conversation_id) {
                  setConversationId(data.conversation_id);
                }
              } else if (data.type === 'error') {
                throw new Error(data.content || 'Unknown error');
              }
            } catch (parseErr) {
              // Skip invalid JSON
            }
          }
        }
      }

      // Mark streaming as complete
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
        )
      );
    } catch (err) {
      console.error('Chat error:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the empty assistant message on error
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [inputValue, isLoading, selectedAgentId, conversationId]);

  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <PageLayout
      title="Chat Test"
      icon={<MessageSquare className="w-6 h-6" />}
      showNavigation={true}
    >
      <div className="max-w-4xl mx-auto">
        {/* Agent Selection */}
        <div
          className={`${THEME.panel.base} ${THEME.panel.border} border rounded-xl p-4 mb-4`}
        >
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className={`text-sm ${THEME.text.muted} mb-1 block`}>
                Select Agent
              </label>
              <Select value={selectedAgentId} onValueChange={setSelectedAgentId}>
                <SelectTrigger className={`${THEME.input.base} w-full`}>
                  <SelectValue placeholder="Choose an agent..." />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-white/20">
                  {agents.map((agent) => (
                    <SelectItem
                      key={agent.id}
                      value={agent.id}
                      className="text-white hover:bg-white/10"
                    >
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {currentAgent && (
              <div className="flex-1">
                <label className={`text-sm ${THEME.text.muted} mb-1 block`}>
                  LLM Provider
                </label>
                <div className={`${THEME.text.secondary} text-sm`}>
                  {currentAgent.llm_provider || 'Not configured'} -{' '}
                  {currentAgent.llm_config?.model || 'default'}
                </div>
              </div>
            )}
            <Button
              variant="outline"
              onClick={clearChat}
              className={`${THEME.button.ghost} mt-5`}
              title="Clear chat"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-4 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Chat Messages */}
        <div
          className={`${THEME.panel.base} ${THEME.panel.border} border rounded-xl mb-4 h-[500px] overflow-hidden flex flex-col`}
        >
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <MessageSquare className={`w-16 h-16 ${THEME.text.muted} mb-4`} />
                <p className={THEME.text.muted}>No messages yet</p>
                <p className={`text-sm ${THEME.text.muted} mt-2`}>
                  Select an agent and start chatting to test function calling
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role !== 'user' && (
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.role === 'tool'
                          ? 'bg-orange-500/20'
                          : 'bg-cyan-500/20'
                      }`}
                    >
                      {message.role === 'tool' ? (
                        <Wrench className="w-4 h-4 text-orange-300" />
                      ) : (
                        <Bot className="w-4 h-4 text-cyan-300" />
                      )}
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-xl p-3 ${
                      message.role === 'user'
                        ? 'bg-cyan-500/20 border border-cyan-500/30'
                        : message.role === 'tool'
                        ? 'bg-orange-500/10 border border-orange-500/20'
                        : 'bg-white/10 border border-white/20'
                    }`}
                  >
                    {message.role === 'tool' && message.toolName && (
                      <div className="text-xs text-orange-300 mb-1 font-medium">
                        Tool: {message.toolName}
                      </div>
                    )}
                    <p
                      className={`whitespace-pre-wrap ${
                        message.role === 'tool'
                          ? 'text-sm text-orange-200 font-mono'
                          : THEME.text.primary
                      }`}
                    >
                      {message.content || (message.isStreaming && '...')}
                    </p>
                    {message.isStreaming && (
                      <Loader2 className="w-4 h-4 animate-spin mt-2 text-cyan-300" />
                    )}
                  </div>
                  {message.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-purple-300" />
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-white/10 p-4">
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedAgentId
                    ? 'Type a message... (try asking about orders)'
                    : 'Select an agent first...'
                }
                disabled={!selectedAgentId || isLoading}
                className={`${THEME.input.base} flex-1`}
              />
              <Button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isLoading || !selectedAgentId}
                className={`${THEME.button.secondary} px-4`}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Help Text */}
        <div className={`text-center ${THEME.text.muted} text-sm`}>
          <p>
            Test your agent&apos;s function calling capabilities. Try asking about
            orders, products, or other tool-enabled features.
          </p>
        </div>
      </div>
    </PageLayout>
  );
}
