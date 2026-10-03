import { useState, useRef, useCallback } from 'react';
import { getToken } from '@/api/client';
import { ChatMessage, SourceItem, CitationItem, GroundingInfo, TurnMetrics } from './types';

interface UseChatStreamOptions {
  conversationId: string | null;
  onTurnComplete?: () => void;
  onError?: (err: Error) => void;
}

export function useChatStream({ conversationId, onTurnComplete, onError }: UseChatStreamOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [streamingSources, setStreamingSources] = useState<SourceItem[]>([]);
  const [streamingCitations, setStreamingCitations] = useState<CitationItem[]>([]);
  const [streamingGrounding, setStreamingGrounding] = useState<GroundingInfo | null>(null);
  const [streamingMetrics, setStreamingMetrics] = useState<TurnMetrics | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setCurrentStatus(null);
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string, activeConvId?: string) => {
      const targetConvId = activeConvId || conversationId;
      if (!text.trim()) return;

      stopStream();

      const userMsgId = `usr-${Date.now()}`;
      const assistantMsgId = `ast-${Date.now()}`;

      const userMsg: ChatMessage = {
        id: userMsgId,
        conversation_id: targetConvId || '',
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      };

      const pendingAssistantMsg: ChatMessage = {
        id: assistantMsgId,
        conversation_id: targetConvId || '',
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, pendingAssistantMsg]);
      setIsStreaming(true);
      setCurrentStatus('Analizando consulta...');
      setStreamingSources([]);
      setStreamingCitations([]);
      setStreamingGrounding(null);
      setStreamingMetrics(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const token = getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      try {
        const response = await fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            conversation_id: targetConvId,
            message: text,
            stream: true,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Error en el servidor: ${response.status} ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulatedText = '';
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = 'message';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            if (trimmed.startsWith('event:')) {
              currentEvent = trimmed.replace('event:', '').trim();
            } else if (trimmed.startsWith('data:')) {
              const dataStr = trimmed.replace('data:', '').trim();
              try {
                const parsed = JSON.parse(dataStr);

                if (currentEvent === 'status') {
                  if (parsed.stage === 'planning') setCurrentStatus('Planificando estrategia de recuperación...');
                  else if (parsed.stage === 'retrieval') setCurrentStatus('Consultando bases de datos y pliegos...');
                  else if (parsed.stage === 'generating') setCurrentStatus('Generando respuesta fundamentada...');
                  else if (parsed.stage === 'anti_hallucination') setCurrentStatus('Validando veracidad y citas...');
                  else setCurrentStatus(parsed.stage || null);
                } else if (currentEvent === 'token') {
                  accumulatedText += parsed.token || '';
                  setMessages((prev) =>
                    prev.map((m) => (m.id === assistantMsgId ? { ...m, content: accumulatedText } : m))
                  );
                } else if (currentEvent === 'citation') {
                  setStreamingCitations((prev) => [...prev, parsed]);
                } else if (currentEvent === 'grounding') {
                  setStreamingGrounding(parsed);
                } else if (currentEvent === 'done') {
                  if (parsed.message_id) {
                    setMessages((prev) =>
                      prev.map((m) => (m.id === assistantMsgId ? { ...m, id: parsed.message_id } : m))
                    );
                  }
                  if (parsed.sources) {
                    setStreamingSources(parsed.sources);
                  }
                  if (parsed.metrics) {
                    setStreamingMetrics(parsed.metrics);
                  }
                }
              } catch {
                // If not JSON, treat data as raw token
                accumulatedText += dataStr;
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantMsgId ? { ...m, content: accumulatedText } : m))
                );
              }
            }
          }
        }

        onTurnComplete?.();
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error('Chat stream failed:', err);
          onError?.(err);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: 'Lo sentimos, ocurrió un error al procesar tu solicitud. Por favor intenta nuevamente.',
                  }
                : m
            )
          );
        }
      } finally {
        setIsStreaming(false);
        setCurrentStatus(null);
        abortControllerRef.current = null;
      }
    },
    [conversationId, stopStream, onTurnComplete, onError]
  );

  return {
    messages,
    setMessages,
    isStreaming,
    currentStatus,
    streamingSources,
    streamingCitations,
    streamingGrounding,
    streamingMetrics,
    sendMessage,
    stopStream,
  };
}
