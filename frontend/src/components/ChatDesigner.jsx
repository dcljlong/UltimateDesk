import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PaperPlaneTilt, Robot, User, Lightning, Sparkle } from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import axios from 'axios';

const getApiUrl = () => {
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (baseUrl) {
    return baseUrl + '/api';
  }
  return '/api';
};
const API = getApiUrl();

const ChatDesigner = ({ params, onParamsUpdate, className = '' }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "G'day! I'm your AI desk designer. Tell me about your dream desk - are you building a gaming battlestation, music studio, or home office? Just describe what you need and I'll configure it for you.",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
const [pendingParams, setPendingParams] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const scrollRef = useRef(null);
  const messagesEndRef = useRef(null);

  const quickPrompts = [
    "Add RGB lighting channels",
    "I need a headset hook",
    "Make it 2m wide",
    "Add a GPU support tray",
    "I want dovetail joints"
  ];

  // Scroll to bottom when messages change
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const sendMessage = async (messageText) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: messageText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const { data } = await axios.post(`${API}/chat/design`, {
        message: messageText,
        current_params: params,
        session_id: sessionId
      });

      if (!sessionId) {
        setSessionId(data.session_id);
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        changes: data.extracted_changes
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (data.updated_params) {
        setPendingParams(data.updated_params);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, I had trouble processing that. Could you try rephrasing your request?",
        timestamp: new Date(),
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleQuickPrompt = (prompt) => {
    sendMessage(prompt);
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center">
            <Robot size={18} className="text-white" />
          </div>
          <div>
            <h3 className="font-bold text-sm">AI Designer</h3>
            <p className="text-xs text-[var(--text-secondary)]">Powered by Gemini</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4" ref={scrollRef}>
        <div className="space-y-4">
          <AnimatePresence>
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                  msg.role === 'user' 
                    ? 'bg-[var(--surface-elevated)]' 
                    : 'bg-[var(--primary)]'
                }`}>
                  {msg.role === 'user' 
                    ? <User size={16} /> 
                    : <Sparkle size={16} className="text-white" />
                  }
                </div>
                <div className={`flex-1 min-w-0 ${msg.role === 'user' ? 'text-right' : ''}`}>
                  <div className={`inline-block rounded-xl px-4 py-3 max-w-[90%] ${
                    msg.role === 'user'
                      ? 'bg-[var(--primary)] text-white'
                      : msg.isError 
                        ? 'bg-red-500/10 border border-red-500/20'
                        : 'neu-surface'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                    
                    {/* Show extracted changes */}
                    {msg.changes && msg.changes.length > 0 && (
  <div className="mt-3 pt-3 border-t border-[var(--border)]">
    <p className="text-xs text-[var(--text-secondary)] mb-2">Suggested changes:</p>

    <div className="flex flex-wrap gap-1 mb-3">
      {msg.changes.map((change, i) => (
        <span
          key={i}
          className="text-xs font-mono bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded"
        >
          {change}
        </span>
      ))}
    </div>

    {pendingParams && (
      <Button
        onClick={() => {
          onParamsUpdate(pendingParams);
          setPendingParams(null);
        }}
        className="btn-primary text-xs px-3 py-1"
      >
        Apply Changes
      </Button>
    )}
  </div>
)}
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center">
                <Sparkle size={16} className="text-white animate-pulse" />
              </div>
              <div className="neu-surface rounded-xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--text-secondary)] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--text-secondary)] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--text-secondary)] animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </motion.div>
          )}
          
          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Quick Prompts */}
      <div className="px-4 py-2 border-t border-[var(--border)]">
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleQuickPrompt(prompt)}
              disabled={isLoading}
              className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full neu-surface hover:bg-[var(--surface-elevated)] transition-smooth disabled:opacity-50"
              data-testid={`quick-prompt-${idx}`}
            >
              <Lightning size={12} className="inline mr-1" />
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-[var(--border)]">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your desk changes..."
            disabled={isLoading}
            className="flex-1 input-field"
            data-testid="chat-input"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn-primary px-4"
            data-testid="chat-submit-btn"
          >
            <PaperPlaneTilt size={20} weight="fill" />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ChatDesigner;



