import { useState, useRef, useEffect } from "react";
import { MessageSquare, X, Send, Bot, Sparkles } from "lucide-react";
import api from "../lib/api";

export default function AIChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hi there! I am your EduNova AI Academic Assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  async function handleSend(e) {
    e.preventDefault();
    if (!input.trim() || busy) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userMessage }]);
    setBusy(true);

    try {
      const { data } = await api.post("/student/ai-chat/", { message: userMessage });
      setMessages((prev) => [...prev, { sender: "bot", text: data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Sorry, I had trouble connecting to the helper. Please try again." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Chat Window */}
      {isOpen && (
        <div className="w-[360px] h-[480px] bg-white/95 backdrop-blur-md rounded-2xl shadow-raised border border-slate-100 flex flex-col overflow-hidden mb-4 transition-all duration-300 transform scale-100 origin-bottom-right">
          {/* Header */}
          <div className="bg-gradient-to-r from-academic-blue to-violet-600 text-white p-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot size={18} />
              </div>
              <div>
                <p className="font-semibold text-sm flex items-center gap-1.5">
                  EduNova AI Assistant <Sparkles size={12} className="text-amber-300 animate-pulse" />
                </p>
                <p className="text-[10px] text-white/80">Online · Powered by AI</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50"
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 max-w-[85%] ${
                  msg.sender === "user" ? "ml-auto flex-row-reverse" : ""
                }`}
              >
                {msg.sender === "bot" && (
                  <div className="w-7 h-7 rounded-full bg-academic-blue/10 flex items-center justify-center text-academic-blue shrink-0">
                    <Bot size={14} />
                  </div>
                )}
                <div
                  className={`rounded-2xl p-3 text-xs leading-relaxed shadow-sm whitespace-pre-wrap ${
                    msg.sender === "user"
                      ? "bg-academic-blue text-white rounded-tr-none"
                      : "bg-white text-slate-800 border border-slate-150 rounded-tl-none"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex gap-2.5 max-w-[85%]">
                <div className="w-7 h-7 rounded-full bg-academic-blue/10 flex items-center justify-center text-academic-blue shrink-0">
                  <Bot size={14} />
                </div>
                <div className="bg-white border border-slate-150 rounded-2xl rounded-tl-none p-3 text-xs shadow-sm flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
              </div>
            )}
          </div>

          {/* Form */}
          <form
            onSubmit={handleSend}
            className="p-3 border-t border-slate-150 bg-white flex gap-2"
          >
            <input
              required
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me: 'What homework is due?'..."
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-academic-blue transition-colors focus:bg-white"
            />
            <button
              type="submit"
              disabled={!input.trim() || busy}
              className="bg-academic-blue hover:bg-academic-blue/90 disabled:opacity-50 text-white rounded-xl p-2 transition-all shadow-sm"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-12 h-12 bg-gradient-to-r from-academic-blue to-violet-600 text-white rounded-full flex items-center justify-center shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 active:scale-95"
        title="Ask AI Assistant"
      >
        {isOpen ? <X size={20} /> : <MessageSquare size={20} />}
      </button>
    </div>
  );
}
