import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Square,
  Plus,
  Trash2,
  Edit2,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  Bot,
  User as UserIcon,
  Clock,
  Database,
  ShieldCheck,
  CheckCircle2,
  Menu,
  X,
  MessageSquare,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import { Conversation, ChatMessage, SourceItem } from './types';
import { useChatStream } from './useChatStream';
import { ControlledMarkdown } from './ControlledMarkdown';
import { SourceCard } from './SourceCard';
import { SuggestedQuestions } from './SuggestedQuestions';

export const ChatView: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [inputText, setInputText] = useState('');
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [feedbackState, setFeedbackState] = useState<Record<string, number>>({});
  const [activeReasonModal, setActiveReasonModal] = useState<string | null>(null);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Stream hook
  const {
    messages,
    setMessages,
    isStreaming,
    currentStatus,
    streamingSources,
    streamingGrounding,
    streamingMetrics,
    sendMessage,
    stopStream,
  } = useChatStream({
    conversationId: activeConvId,
    onTurnComplete: () => {
      fetchConversations();
    },
  });

  // Fetch conversations list
  const fetchConversations = async () => {
    try {
      const res = await apiClient.get<Conversation[]>('/chat/conversations');
      setConversations(res.data);
      if (!activeConvId && res.data.length > 0) {
        selectConversation(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, currentStatus]);

  // Select a conversation and load its message history
  const selectConversation = async (convId: string) => {
    setActiveConvId(convId);
    setIsSidebarOpen(false);
    try {
      const res = await apiClient.get<{ conversation: Conversation; messages: ChatMessage[] }>(
        `/chat/conversations/${convId}`
      );
      setMessages(res.data.messages || []);
    } catch (err) {
      console.error('Failed to load conversation details:', err);
    }
  };

  // Create a new conversation
  const handleNewConversation = async () => {
    try {
      const res = await apiClient.post<Conversation>('/chat/conversations', {
        title: 'Nueva consulta',
      });
      setConversations((prev) => [res.data, ...prev]);
      setActiveConvId(res.data.id);
      setMessages([]);
      setIsSidebarOpen(false);
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (!window.confirm('¿Seguro que deseas eliminar esta conversación?')) return;

    try {
      await apiClient.delete(`/chat/conversations/${convId}`);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        const remaining = conversations.filter((c) => c.id !== convId);
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Rename conversation
  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditingTitle(conv.title || '');
  };

  const handleSaveRename = async (convId: string) => {
    if (!editingTitle.trim()) return;
    try {
      await apiClient.patch(`/chat/conversations/${convId}`, { title: editingTitle.trim() });
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: editingTitle.trim() } : c))
      );
      setEditingConvId(null);
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  };

  // Submit query
  const handleSend = () => {
    if (!inputText.trim() || isStreaming) return;
    const text = inputText;
    setInputText('');
    sendMessage(text, activeConvId || undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Feedback handling
  const handleFeedback = async (messageId: string, rating: 1 | -1) => {
    setFeedbackState((prev) => ({ ...prev, [messageId]: rating }));
    if (rating === -1) {
      setActiveReasonModal(messageId);
    } else {
      try {
        await apiClient.post(`/chat/messages/${messageId}/feedback`, {
          message_id: messageId,
          rating: 1,
        });
      } catch (err) {
        console.error('Feedback failed:', err);
      }
    }
  };

  const submitNegativeFeedback = async (messageId: string, reason: string) => {
    try {
      await apiClient.post(`/chat/messages/${messageId}/feedback`, {
        message_id: messageId,
        rating: -1,
        reason,
        comment: feedbackComment,
      });
    } catch (err) {
      console.error('Feedback submission error:', err);
    } finally {
      setActiveReasonModal(null);
      setFeedbackComment('');
    }
  };

  return (
    <div className="flex h-[760px] w-full rounded-2xl border border-border/80 bg-background shadow-xl overflow-hidden relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar: Conversations List */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-card border-r border-border p-4 flex flex-col transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2 font-bold text-sm text-foreground">
            <Sparkles className="h-4 w-4 text-primary" />
            MercadoInsight AI
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden p-1 text-muted-foreground hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <button
          onClick={handleNewConversation}
          className="mt-3 flex items-center justify-center gap-2 w-full px-3 py-2 rounded-xl text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
        >
          <Plus className="h-3.5 w-3.5" />
          Nueva Conversación
        </button>

        <div className="mt-4 flex-1 overflow-y-auto space-y-1 pr-1">
          <span className="text-[11px] font-semibold text-muted-foreground px-2 uppercase tracking-wider">
            Historial de sesiones
          </span>
          {conversations.length === 0 && (
            <p className="text-xs text-muted-foreground p-2">Sin conversaciones aún.</p>
          )}
          {conversations.map((conv) => {
            const isActive = conv.id === activeConvId;
            const isEditing = editingConvId === conv.id;

            return (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary font-medium border border-primary/20'
                    : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
                }`}
              >
                {isEditing ? (
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onBlur={() => handleSaveRename(conv.id)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(conv.id)}
                    autoFocus
                    className="bg-background px-1 py-0.5 rounded border border-primary w-full text-foreground text-xs"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{conv.title || 'Nueva consulta'}</span>
                  </div>
                )}

                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity shrink-0">
                  <button
                    onClick={(e) => handleStartRename(e, conv)}
                    className="p-1 hover:text-foreground text-muted-foreground"
                    title="Renombrar"
                  >
                    <Edit2 className="h-3 w-3" />
                  </button>
                  <button
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    className="p-1 hover:text-destructive text-muted-foreground"
                    title="Eliminar"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-3 border-t border-border/80 text-[11px] text-muted-foreground flex items-center justify-between">
          <span>RAG v2.0 • Híbrido</span>
          <span className="flex items-center gap-1 text-emerald-500 font-medium">
            <CheckCircle2 className="h-3 w-3" /> Online
          </span>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-card/20 min-w-0">
        {/* Top bar */}
        <div className="h-14 border-b border-border/80 px-4 flex items-center justify-between bg-card/60 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-1.5 rounded-lg border border-border text-foreground hover:bg-muted"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-xs font-bold text-foreground truncate max-w-[220px] sm:max-w-md">
                {conversations.find((c) => c.id === activeConvId)?.title || 'Asistente de Mercado Público'}
              </h2>
              <span className="text-[10px] text-muted-foreground">
                Grounding en tiempo real • Consultas SQL controladas y embeddings
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="h-3 w-3" />
              ChileCompra IA
            </span>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {messages.length === 0 && (
            <SuggestedQuestions onSelectQuestion={(q) => sendMessage(q, activeConvId || undefined)} />
          )}

          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const feedbackVal = feedbackState[msg.id];

            return (
              <div
                key={msg.id || idx}
                className={`flex gap-3 max-w-4xl mx-auto ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`relative rounded-2xl p-4 text-xs md:text-sm max-w-[85%] md:max-w-[78%] shadow-sm ${
                    isUser
                      ? 'bg-primary text-primary-foreground rounded-tr-sm ml-auto'
                      : 'bg-card border border-border/80 text-foreground rounded-tl-sm space-y-3'
                  }`}
                >
                  {isUser ? (
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <>
                      <ControlledMarkdown content={msg.content} />

                      {/* Sources Cards if available */}
                      {streamingSources.length > 0 && idx === messages.length - 1 && (
                        <div className="mt-3 pt-3 border-t border-border/60">
                          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block mb-2">
                            Fuentes verificadas ({streamingSources.length})
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {streamingSources.map((src: SourceItem, sIdx: number) => (
                              <SourceCard key={src.id || sIdx} source={src} index={sIdx} />
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Metrics & Grounding footer */}
                      <div className="mt-3 pt-2 border-t border-border/40 flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground">
                        <div className="flex items-center gap-3">
                          {streamingMetrics?.latency_ms && idx === messages.length - 1 && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {streamingMetrics.latency_ms.toFixed(0)} ms
                            </span>
                          )}
                          {streamingMetrics?.retrieval_ms && idx === messages.length - 1 && (
                            <span className="flex items-center gap-1">
                              <Database className="h-3 w-3" />
                              {streamingMetrics.retrieval_ms.toFixed(0)} ms
                            </span>
                          )}
                          {streamingGrounding?.supported && (
                            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                              <ShieldCheck className="h-3 w-3" />
                              Evidencia respaldada
                            </span>
                          )}
                        </div>

                        {/* Feedback buttons */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleFeedback(msg.id, 1)}
                            className={`p-1 rounded hover:bg-muted transition-colors ${
                              feedbackVal === 1 ? 'text-emerald-500 font-bold' : 'text-muted-foreground'
                            }`}
                            title="Respuesta precisa"
                          >
                            <ThumbsUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, -1)}
                            className={`p-1 rounded hover:bg-muted transition-colors ${
                              feedbackVal === -1 ? 'text-destructive font-bold' : 'text-muted-foreground'
                            }`}
                            title="Reportar problema"
                          >
                            <ThumbsDown className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>

                {isUser && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground border border-border">
                    <UserIcon className="h-4 w-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Real-time Streaming Status Badge */}
          {isStreaming && currentStatus && (
            <div className="flex items-center gap-2 text-xs text-primary max-w-4xl mx-auto pl-11 animate-pulse">
              <Sparkles className="h-3.5 w-3.5" />
              <span>{currentStatus}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-border/80 bg-card/40 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto flex items-end gap-2 rounded-2xl border border-border/90 bg-card p-2 shadow-sm focus-within:border-primary/50 transition-colors">
            <textarea
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Haz una pregunta sobre compras públicas, licitaciones u organismos..."
              className="flex-1 max-h-32 min-h-[38px] resize-none bg-transparent px-3 py-2 text-xs md:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            />

            {isStreaming ? (
              <button
                onClick={stopStream}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-all shadow-sm"
                title="Detener respuesta"
              >
                <Square className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!inputText.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                title="Enviar consulta"
              >
                <Send className="h-4 w-4" />
              </button>
            )}
          </div>
          <div className="max-w-4xl mx-auto mt-2 text-center text-[10px] text-muted-foreground">
            MercadoInsight AI puede cometer errores. Verifica la información contrastando las fuentes oficiales citadas.
          </div>
        </div>
      </div>

      {/* Negative Feedback Modal */}
      {activeReasonModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground">Reportar respuesta</h3>
              <button onClick={() => setActiveReasonModal(null)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              Ayúdanos a mejorar el modelo indicando el motivo de tu calificación negativa:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {[
                { id: 'hallucination', label: 'Datos inventados / Alucinación' },
                { id: 'wrong_sources', label: 'Fuentes erróneas' },
                { id: 'irrelevant', label: 'Respuesta irrelevante' },
                { id: 'incomplete', label: 'Respuesta incompleta' },
              ].map((r) => (
                <button
                  key={r.id}
                  onClick={() => submitNegativeFeedback(activeReasonModal, r.id)}
                  className="p-2.5 rounded-lg border border-border/80 bg-muted/30 hover:bg-muted text-foreground text-left transition-colors font-medium"
                >
                  {r.label}
                </button>
              ))}
            </div>

            <textarea
              rows={2}
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="Comentario adicional opcional..."
              className="w-full p-2 text-xs rounded-lg border border-border bg-background text-foreground"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatView;
