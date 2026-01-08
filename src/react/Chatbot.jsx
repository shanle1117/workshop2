import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * React Chatbot Component with react-markdown support
 */
function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      content: "👋 Hello! Welcome to FAIX AI Chatbot. I'm here to help you with questions about course registration, staff contacts, schedules, and other student inquiries. How can I assist you today?",
      timestamp: new Date(),
      feedbackSubmitted: undefined, // Allow feedback on welcome message
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  
  // Keep ref in sync with state
  useEffect(() => {
    inputValueRef.current = inputValue;
  }, [inputValue]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [agentId, setAgentId] = useState('faq');
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState('Online');
  
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const pendingTranscriptRef = useRef('');
  const inputRef = useRef(null);
  const inputValueRef = useRef('');
  
  const API_BASE_URL = 'http://localhost:8000';

  // Initialize session ID
  useEffect(() => {
    let storedSessionId = localStorage.getItem('chatbot_session_id');
    if (!storedSessionId) {
      storedSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('chatbot_session_id', storedSessionId);
    }
    setSessionId(storedSessionId);
    
    // Set welcome time
    const timeElement = document.getElementById('welcome-time');
    if (timeElement) {
      timeElement.textContent = formatTime(new Date());
    }
  }, []);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    recognition.onstart = () => {
      setIsRecording(true);
      pendingTranscriptRef.current = '';
      setStatus('Listening...');
    };
    
    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }
      
      if (finalTranscript.trim()) {
        pendingTranscriptRef.current += finalTranscript;
      }
      
      const displayText = pendingTranscriptRef.current + interimTranscript;
      if (displayText.trim()) {
        setInputValue(displayText.trim());
      }
    };
    
    recognition.onerror = (event) => {
      handleSpeechError(event.error);
    };
    
    recognition.onend = () => {
      setIsRecording(false);
      setStatus('Online');
      
      if (pendingTranscriptRef.current.trim()) {
        const finalText = pendingTranscriptRef.current.trim();
        pendingTranscriptRef.current = '';
        handleSpeechResult(finalText);
      } else if (inputValueRef.current.trim()) {
        const inputText = inputValueRef.current.trim();
        setInputValue('');
        handleSpeechResult(inputText);
      }
    };
    
    recognitionRef.current = recognition;
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []); // Remove inputValue dependency to prevent recreation on every input change

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  };

  const apiCall = async (url, options = {}) => {
    const csrftoken = getCookie('csrftoken');
    if (csrftoken) {
      options.headers = options.headers || {};
      options.headers['X-CSRFToken'] = csrftoken;
    }

    const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
    return fetch(fullUrl, options);
  };

  const sendMessage = async () => {
    const message = inputValue.trim();
    
    if (!message || isLoading) {
      return;
    }
    
    setInputValue('');
    
    // Add user message
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setHistory(prev => [...prev, { role: 'user', content: message }]);
    
    setIsLoading(true);
    
    try {
      const response = await apiCall('/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId,
          agent_id: agentId,
          history: history.slice(-10),
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.session_id) {
          setSessionId(data.session_id);
          localStorage.setItem('chatbot_session_id', data.session_id);
        }
        if (data.conversation_id) {
          setConversationId(data.conversation_id);
        }
        
        if (data.response) {
          const botMessage = {
            role: 'bot',
            content: data.response,
            timestamp: new Date(),
            pdfUrl: data.pdf_url,
            messageId: data.message_id, // Store message ID for feedback
            conversationId: data.conversation_id,
            intent: data.intent,
            userMessage: message, // Store the user message that prompted this response
            feedbackSubmitted: undefined, // Explicitly allow feedback buttons
          };
          setMessages(prev => [...prev, botMessage]);
          setHistory(prev => [...prev, { role: 'assistant', content: data.response }]);
        } else {
          addBotMessage('Sorry, I received an empty response. Please try again.');
        }
      } else {
        let errorMessage = 'Sorry, I encountered an error. Please try again.';
        
        if (response.status === 404) {
          errorMessage = 'Chat service not found. Please contact support.';
        } else if (response.status === 400) {
          errorMessage = 'Invalid request. Please check your message and try again.';
        } else if (response.status >= 500) {
          errorMessage = 'Server error occurred. Please try again in a moment.';
        }
        
        try {
          const error = await response.json();
          if (error.detail || error.message) {
            errorMessage = `Error: ${error.detail || error.message}`;
          }
        } catch (jsonError) {
          console.error('Chat API error:', response.status, response.statusText);
        }
        
        addBotMessage(errorMessage);
      }
    } catch (error) {
      let errorMessage = "Sorry, I couldn't connect to the server. Please check your connection.";
      
      if (error.message) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          errorMessage = 'Network error. Please check your internet connection and try again.';
        } else if (error.message.includes('Invalid response')) {
          errorMessage = 'Server returned an invalid response. Please try again.';
        }
      }
      
      addBotMessage(errorMessage);
      console.error('Network error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const addBotMessage = (content) => {
    const botMessage = {
      role: 'bot',
      content: content,
      timestamp: new Date(),
      feedbackSubmitted: undefined, // Ensure feedback buttons can show
    };
    setMessages(prev => [...prev, botMessage]);
  };

  const submitFeedback = async (messageIndex, feedbackType) => {
    const message = messages[messageIndex];
    if (!message || message.role !== 'bot') {
      return;
    }

    // Optimistically update UI
    setMessages(prev => prev.map((msg, idx) => 
      idx === messageIndex 
        ? { ...msg, feedbackSubmitted: feedbackType }
        : msg
    ));

    try {
      // Only submit if we have a messageId (newer messages)
      if (message.messageId) {
        const response = await apiCall('/api/feedback/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message_id: message.messageId,
            conversation_id: message.conversationId || conversationId,
            feedback_type: feedbackType,
            user_message: message.userMessage || '',
            bot_response: message.content,
            intent: message.intent,
            session_id: sessionId,
          }),
        });

        if (!response.ok) {
          console.error('Failed to submit feedback');
          // Revert optimistic update on error
          setMessages(prev => prev.map((msg, idx) => 
            idx === messageIndex 
              ? { ...msg, feedbackSubmitted: undefined }
              : msg
          ));
        }
      } else {
        // For older messages without messageId, still show confirmation
        // but we can't store it in the database
        console.log(`Feedback received (${feedbackType}) for message without ID`);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      // Revert optimistic update on error
      setMessages(prev => prev.map((msg, idx) => 
        idx === messageIndex 
          ? { ...msg, feedbackSubmitted: undefined }
          : msg
      ));
    }
  };

  const toggleSpeechRecognition = () => {
    if (!recognitionRef.current) {
      addBotMessage('Speech recognition is not supported in your browser. Please use Chrome or Edge for voice input.');
      return;
    }
    
    if (isRecording) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  };

  const startSpeechRecognition = () => {
    if (!recognitionRef.current || isRecording || isLoading) {
      return;
    }
    
    try {
      setInputValue('');
      recognitionRef.current.start();
    } catch (error) {
      console.error('Error starting speech recognition:', error);
      handleSpeechError('start-failed');
    }
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
    }
  };

  const handleSpeechResult = (transcript) => {
    if (!transcript || !transcript.trim()) {
      return;
    }
    
    setInputValue(transcript);
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  const handleSpeechError = (error) => {
    setIsRecording(false);
    setStatus('Online');
    
    let errorMessage = 'Speech recognition error occurred.';
    
    switch (error) {
      case 'no-speech':
        errorMessage = 'No speech detected. Please try again.';
        break;
      case 'audio-capture':
        errorMessage = 'No microphone found. Please check your microphone settings.';
        break;
      case 'not-allowed':
        errorMessage = 'Microphone permission denied. Please allow microphone access and try again.';
        break;
      case 'network':
        errorMessage = 'Network error occurred during speech recognition.';
        break;
      case 'aborted':
        return;
      case 'start-failed':
        errorMessage = 'Failed to start speech recognition. Please try again.';
        break;
      default:
        console.error('Speech recognition error:', error);
    }
    
    setTimeout(() => {
      if (error !== 'aborted') {
        addBotMessage(errorMessage);
      }
    }, 100);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chatbot-widget">
      <div
        id="chatbot-toggle"
        className="chatbot-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      
      {isOpen && (
        <div id="chatbot-container" className="chatbot-container">
          <div className="chatbot-header">
            <div className="chatbot-header-content">
              <h3>FAIX Assistant</h3>
              <p className="chatbot-status">{status}</p>
            </div>
            <button
              id="chatbot-minimize"
              className="chatbot-minimize"
              onClick={() => setIsOpen(false)}
            >
              −
            </button>
          </div>
          
          <div className="chatbot-messages" id="chatbot-messages">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}-message`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  <div className="message-text">
                    {msg.role === 'bot' || msg.role === 'assistant' ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ node, ...props }) => (
                            <a target="_blank" rel="noopener noreferrer" {...props} />
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      <p>{msg.content}</p>
                    )}
                  </div>
                  {msg.pdfUrl && (
                    <div className="pdf-container" style={{ marginTop: '12px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
                      <a
                        href={msg.pdfUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="pdf-link"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', background: '#007bff', color: 'white', borderRadius: '6px', textDecoration: 'none', fontWeight: '500' }}
                      >
                        📚 View Academic Handbook PDF
                      </a>
                    </div>
                  )}
                  {/* Feedback buttons - show for all bot messages without feedback */}
                  {(msg.role === 'bot' || msg.role === 'assistant') && !msg.feedbackSubmitted && (
                    <div className="feedback-buttons" style={{ 
                      marginTop: '12px', 
                      padding: '10px 14px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '8px',
                      border: '1px solid #e0e0e0',
                      display: 'flex', 
                      gap: '10px', 
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      boxSizing: 'border-box',
                      position: 'relative',
                      zIndex: 10,
                      visibility: 'visible',
                      opacity: 1
                    }}>
                      <span style={{ fontSize: '13px', color: '#495057', fontWeight: '500', flexShrink: 0 }}>
                        Was this answer helpful?
                      </span>
                      <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                        <button
                          onClick={() => submitFeedback(index, 'good')}
                          type="button"
                          style={{
                            padding: '6px 16px',
                            fontSize: '13px',
                            border: '1px solid #28a745',
                            background: '#28a745',
                            color: 'white',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontWeight: '500',
                            transition: 'all 0.2s ease',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                            whiteSpace: 'nowrap'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = '#218838';
                            e.currentTarget.style.transform = 'scale(1.05)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = '#28a745';
                            e.currentTarget.style.transform = 'scale(1)';
                          }}
                          title="This answer was helpful"
                        >
                          <span>👍</span>
                          <span>Good</span>
                        </button>
                        <button
                          onClick={() => submitFeedback(index, 'bad')}
                          type="button"
                          style={{
                            padding: '6px 16px',
                            fontSize: '13px',
                            border: '1px solid #dc3545',
                            background: '#dc3545',
                            color: 'white',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontWeight: '500',
                            transition: 'all 0.2s ease',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                            whiteSpace: 'nowrap'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = '#c82333';
                            e.currentTarget.style.transform = 'scale(1.05)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = '#dc3545';
                            e.currentTarget.style.transform = 'scale(1)';
                          }}
                          title="This answer needs improvement"
                        >
                          <span>👎</span>
                          <span>Not Good</span>
                        </button>
                      </div>
                    </div>
                  )}
                  {msg.role === 'bot' && msg.feedbackSubmitted && (
                    <div style={{ 
                      marginTop: '12px', 
                      padding: '8px 12px',
                      fontSize: '13px', 
                      color: msg.feedbackSubmitted === 'good' ? '#28a745' : '#dc3545',
                      backgroundColor: msg.feedbackSubmitted === 'good' ? '#d4edda' : '#f8d7da',
                      border: `1px solid ${msg.feedbackSubmitted === 'good' ? '#c3e6cb' : '#f5c6cb'}`,
                      borderRadius: '6px',
                      fontWeight: '500',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <span>✓</span>
                      <span>{msg.feedbackSubmitted === 'good' ? 'Thank you for your feedback! This helps us improve.' : 'Thanks for helping us improve! We\'ll work on better answers.'}</span>
                    </div>
                  )}
                  <span className="message-time">{formatTime(msg.timestamp)}</span>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="chatbot-typing" id="chatbot-typing">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="chatbot-input-container">
            <input
              ref={inputRef}
              type="text"
              id="chatbot-input"
              className="chatbot-input"
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              autoComplete="off"
            />
            <button
              id="chatbot-mic"
              className={`chatbot-mic ${isRecording ? 'mic-recording' : 'mic-inactive'}`}
              onClick={toggleSpeechRecognition}
              disabled={isLoading || !recognitionRef.current}
              title={isRecording ? 'Stop recording' : 'Voice input'}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            </button>
            <button
              id="chatbot-send"
              className="chatbot-send"
              onClick={sendMessage}
              disabled={isLoading}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chatbot;

