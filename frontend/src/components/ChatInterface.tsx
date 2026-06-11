import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Send, MoreVertical } from 'lucide-react';
import { 
  getOrCreateUserId, 
  getOrCreateSessionId, 
  sendStreamingMessage, 
  clearSession 
} from '../api/client';

interface Message {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: Date;
}

export interface ChatInterfaceProps {
  isTestMode?: boolean;
}

const renderFormattedText = (text: string): React.ReactNode[] => {
  if (!text) return [];
  const regex = /(\*\*[^\s\*](?:[^\*]*?[^\s\*])?\*\*|\*[^\s\*](?:[^\*]*?[^\s\*])?\*)/g;
  const parts = text.split(regex);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-slate-100">
          {part.slice(2, -2)}
        </strong>
      );
    } else if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <em key={index} className="italic text-slate-200">
          {part.slice(1, -1)}
        </em>
      );
    }
    return part;
  });
};

const ChatInterface: React.FC<ChatInterfaceProps> = ({ isTestMode = false }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: 'Halo! Saya Tanya Makmur, asisten virtual Anda. Ada yang bisa saya bantu hari ini?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep track of user and session identities in component state
  const [userId, setUserId] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const uId = getOrCreateUserId();
        setUserId(uId);
        const sId = await getOrCreateSessionId(uId);
        setSessionId(sId);
      } catch (err) {
        // Secure logging: do not print user secrets or raw inputs in console log statements
        console.error('Failed to initialize chat session on mount');
      }
    };
    initSession();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Auto scroll to bottom when messages list, loading, or typing state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isTyping]);

  const handleResetSession = async () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    clearSession();
    setMessages([
      {
        id: 'welcome',
        sender: 'agent',
        text: 'Halo! Saya Tanya Makmur, asisten virtual Anda. Ada yang bisa saya bantu hari ini?',
        timestamp: new Date(),
      },
    ]);
    try {
      const uId = getOrCreateUserId();
      setUserId(uId);
      const sId = await getOrCreateSessionId(uId, true);
      setSessionId(sId);
    } catch (err) {
      // Secure logging: do not print user secrets or raw inputs in console log statements
      console.error('Failed to re-initialize session');
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    // Create user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: trimmedInput,
      timestamp: new Date(),
    };

    // Update messages list, clear input, and show loading/typing
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setIsTyping(true);

    const delay = isTestMode ? 0 : 1000;
    
    try {
      // Ensure credentials are available
      const currentUserId = userId || getOrCreateUserId();
      if (!userId) setUserId(currentUserId);

      const currentSessionId = sessionId || await getOrCreateSessionId(currentUserId);
      if (!sessionId) setSessionId(currentSessionId);

      let agentMsgId: string | null = null;

      // Stream chat completion chunks
      await sendStreamingMessage(currentUserId, currentSessionId, trimmedInput, (chunk) => {
        // Hide the typing bouncing dots once the first chunk of response arrives
        setIsTyping(false);

        if (!agentMsgId) {
          agentMsgId = `agent-${Date.now()}`;
          setMessages((prev) => [
            ...prev,
            {
              id: agentMsgId!,
              sender: 'agent',
              text: chunk,
              timestamp: new Date(),
            },
          ]);
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === agentMsgId
                ? { ...msg, text: msg.text + chunk }
                : msg
            )
          );
        }
      });

      // Stream successfully completed
      setIsLoading(false);
      setIsTyping(false);
    } catch (error) {
      console.error('sendStreamingMessage error:', error);
      // Fallback offline mock response logic
      let replyText = 'Terima kasih atas pertanyaan Anda. Tanya Makmur siap membantu kebutuhan perbankan Anda.';
      const lowerInput = trimmedInput.toLowerCase();

      if (lowerInput.includes('saldo')) {
        replyText = 'Saldo akun Anda aman dan terjaga. Anda dapat memeriksa saldo melalui menu Rekening Utama.';
      } else if (lowerInput.includes('bunga')) {
        replyText = 'Suku bunga tabungan Bank Makmur saat ini adalah 4.5% per tahun.';
      } else if (lowerInput.includes('pinjaman')) {
        replyText = 'Kami menawarkan berbagai produk pinjaman dengan syarat mudah dan proses cepat. Silakan hubungi kantor cabang terdekat.';
      } else if (lowerInput.includes('halo') || lowerInput.includes('hai')) {
        replyText = 'Halo! Ada yang bisa saya bantu hari ini terkait layanan Bank Makmur?';
      }

      // Simulate a conversation delay to make the mock response feel natural
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        const agentMsg: Message = {
          id: `agent-${Date.now()}`,
          sender: 'agent',
          text: replyText,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, agentMsg]);
        setIsLoading(false);
        setIsTyping(false);
        timeoutRef.current = null;
      }, delay);
    }
  };

  return (
    <div className="flex flex-col w-full max-w-lg h-screen sm:h-[650px] bg-slate-900 sm:rounded-2xl sm:shadow-2xl overflow-hidden border border-slate-800">
      {/* Header section */}
      <header className="flex items-center justify-between px-4 py-3 bg-slate-800/80 backdrop-blur-md border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <button 
            type="button" 
            onClick={handleResetSession}
            className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
            aria-label="Back"
          >
            <ArrowLeft size={20} />
          </button>
          
          {/* Avatar: Aurora gradient square logo with 'M' in the center */}
          <div className="w-10 h-10 rounded-xl bg-aurora-gradient flex items-center justify-center font-bold text-white shadow-lg text-lg select-none">
            M
          </div>
          
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-white tracking-wide">Tanya Makmur</span>
              {/* Green online dot */}
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" aria-label="Online"></span>
            </div>
            <span className="text-xs text-slate-400">Asisten Virtual</span>
          </div>
        </div>
        
        <button 
          type="button" 
          className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
          aria-label="More options"
        >
          <MoreVertical size={20} />
        </button>
      </header>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/40">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div 
              key={msg.id} 
              className={`flex items-end gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {/* Agent Avatar next to agent bubbles */}
              {!isUser && (
                <div className="w-8 h-8 rounded-lg bg-aurora-gradient flex items-center justify-center font-bold text-white shadow text-xs select-none flex-shrink-0">
                  M
                </div>
              )}
              
              <div 
                className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                  isUser 
                    ? 'bg-slate-200 text-slate-900 rounded-tr-none border border-slate-300' 
                    : 'bg-slate-900 text-slate-100 rounded-tl-none border border-slate-800'
                }`}
              >
                <p className="whitespace-pre-wrap">{renderFormattedText(msg.text)}</p>
                <span className="block text-[10px] text-right mt-1 text-slate-500 select-none">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading / Typing indicator (displayed only when isTyping is true) */}
        {isTyping && (
          <div className="flex items-end gap-2.5 justify-start" data-testid="typing-indicator" aria-live="polite" role="status">
            <div className="w-8 h-8 rounded-lg bg-aurora-gradient flex items-center justify-center font-bold text-white shadow text-xs select-none flex-shrink-0">
              M
            </div>
            <div className="bg-slate-900 text-slate-100 rounded-2xl rounded-tl-none px-4 py-3 border border-slate-800 shadow-sm flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <footer className="p-4 bg-slate-900 border-t border-slate-800/80">
        <form onSubmit={handleSend} className="gradient-border-wrapper">
          <div className="gradient-border-content flex items-center px-4 py-1.5">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              placeholder={isLoading ? 'Looking up that information for you...' : 'Tulis pesan...'}
              className="flex-1 bg-transparent text-white placeholder-slate-400 text-sm focus:outline-none disabled:cursor-not-allowed py-1.5"
              aria-label="Tulis pesan"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-1.5 ml-2 rounded-full text-indigo-400 hover:text-white hover:bg-slate-800 disabled:text-slate-600 disabled:bg-transparent transition-all"
              aria-label="Kirim"
            >
              <Send size={18} />
            </button>
          </div>
        </form>
      </footer>
    </div>
  );
};

export default ChatInterface;
