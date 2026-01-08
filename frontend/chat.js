/**
 * Chatbot JavaScript for FAIX Chatbot
 * Handles real-time chat interaction with AJAX calls to Django API
 */

// Base URL for the backend API.
// In development, this can point to your local Django server.
// For production, update this to your deployed backend URL.
const API_BASE_URL = 'http://localhost:8000';

// Configure marked.js for markdown parsing
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,      // Convert \n to <br>
        gfm: true,         // GitHub Flavored Markdown
        headerIds: false,  // Don't add IDs to headers
        mangle: false,     // Don't mangle email addresses
        sanitize: false,   // We handle sanitization separately
    });
}

class Chatbot {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
        this.conversationId = null;
        this.agentId = 'faq';
        this.history = [];
        this.isOpen = false;
        this.isLoading = false;
        this.isRecording = false;
        this.recognition = null;
        this.speechSupported = false;
        
        this.initializeElements();
        this.initializeSpeechRecognition();
        this.attachEventListeners();
        this.loadConversationHistory();
        
        // Set welcome message time
        this.setWelcomeTime();
    }
    
    initializeElements() {
        this.toggle = document.getElementById('chatbot-toggle');
        this.container = document.getElementById('chatbot-container');
        this.minimize = document.getElementById('chatbot-minimize');
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.input = document.getElementById('chatbot-input');
        this.sendButton = document.getElementById('chatbot-send');
        this.micButton = document.getElementById('chatbot-mic');
        this.typingIndicator = document.getElementById('chatbot-typing');
        this.status = document.getElementById('chatbot-status');
        this.badge = document.getElementById('chatbot-badge');
        // Optional agent selector (e.g., dropdown or tabs)
        this.agentSelect = document.getElementById('chatbot-agent-select');
    }
    
    initializeSpeechRecognition() {
        // Check for browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            this.speechSupported = false;
            if (this.micButton) {
                this.micButton.style.display = 'none';
            }
            return;
        }
        
        this.speechSupported = true;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        // Track transcribed text to avoid duplicate sends
        this.pendingTranscript = '';
        
        // Set up recognition event handlers
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.pendingTranscript = '';
            this.updateMicButtonState('recording');
            this.updateStatus('Listening...');
        };
        
        this.recognition.onresult = (event) => {
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
            
            // Accumulate final transcript
            if (finalTranscript.trim()) {
                this.pendingTranscript += finalTranscript;
            }
            
            // Update input field with combined final and interim results
            const displayText = this.pendingTranscript + interimTranscript;
            if (displayText.trim() && this.input) {
                this.input.value = displayText.trim();
            }
        };
        
        this.recognition.onerror = (event) => {
            this.handleSpeechError(event.error);
        };
        
        this.recognition.onend = () => {
            this.isRecording = false;
            this.updateMicButtonState('inactive');
            this.updateStatus('Online');
            
            // Process final transcript when recognition ends
            if (this.pendingTranscript.trim()) {
                const finalText = this.pendingTranscript.trim();
                this.pendingTranscript = '';
                this.handleSpeechResult(finalText);
            } else if (this.input && this.input.value.trim()) {
                // If we have text in input but no final transcript, use input value
                const inputText = this.input.value.trim();
                this.input.value = '';
                this.handleSpeechResult(inputText);
            }
        };
    }
    
    attachEventListeners() {
        // Toggle chatbot
        if (this.toggle) {
            this.toggle.addEventListener('click', () => this.toggleChatbot());
        }
        if (this.minimize) {
            this.minimize.addEventListener('click', () => this.toggleChatbot());
        }
        
        // Send message
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        if (this.input) {
            this.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize input
            this.input.addEventListener('input', () => {
                this.input.style.height = 'auto';
                this.input.style.height = this.input.scrollHeight + 'px';
            });
        }

        // Agent selector change
        if (this.agentSelect) {
            this.agentSelect.addEventListener('change', (e) => {
                const value = e.target.value || 'faq';
                this.agentId = value;
            });
        }
        
        // Microphone button
        if (this.micButton) {
            this.micButton.addEventListener('click', () => this.toggleSpeechRecognition());
        }
    }
    
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('chatbot_session_id');
        if (!sessionId) {
            sessionId = this.generateSessionId();
            localStorage.setItem('chatbot_session_id', sessionId);
        }
        return sessionId;
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    toggleChatbot() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            if (this.container) {
                this.container.style.display = 'flex';
            }
            if (this.input) {
                this.input.focus();
            }
            this.hideBadge();
        } else {
            if (this.container) {
                this.container.style.display = 'none';
            }
        }
    }
    
    setWelcomeTime() {
        const timeElement = document.getElementById('welcome-time');
        if (timeElement) {
            timeElement.textContent = this.formatTime(new Date());
        }
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    async sendMessage() {
        if (!this.input) {
            console.error('Chatbot input element not found');
            return;
        }
        
        const message = this.input.value.trim();
        
        if (!message || this.isLoading) {
            return;
        }
        
        // Clear input
        this.input.value = '';
        this.input.style.height = 'auto';
        
        // Add user message to UI
        this.addMessage('user', message);
        // Track user turn in history for LLM context
        this.history.push({ role: 'user', content: message });
        
        // Show typing indicator
        this.showTyping();
        this.setLoading(true);
        
        try {
            const response = await this.apiCall('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId,
                        agent_id: this.agentId,
                        // Send compact history (last 10 turns)
                        history: this.history.slice(-10),
                }),
            });
            
            if (response.ok) {
                let data;
                try {
                    data = await response.json();
                } catch (jsonError) {
                    throw new Error('Invalid response format from server');
                }
                
                // Update session and conversation IDs
                if (data.session_id) {
                    this.sessionId = data.session_id;
                    localStorage.setItem('chatbot_session_id', this.sessionId);
                }
                if (data.conversation_id) {
                    this.conversationId = data.conversation_id;
                }
                
                // Add bot response to UI with feedback data
                this.hideTyping();
                if (data.response) {
                    this.addMessage('bot', data.response, data.pdf_url, data.message_id, data.intent, message);
                    // Track assistant turn in history
                    this.history.push({ role: 'assistant', content: data.response });
                } else {
                    this.addMessage('bot', 'Sorry, I received an empty response. Please try again.', null, null, null, null);
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
                    console.error('Chat API error:', error);
                    if (error.detail || error.message) {
                        errorMessage = `Error: ${error.detail || error.message}`;
                    }
                } catch (jsonError) {
                    console.error('Chat API error (non-JSON):', response.status, response.statusText);
                }
                
                this.hideTyping();
                this.addMessage('bot', errorMessage, null, null, null, null);
            }
        } catch (error) {
            this.hideTyping();
            let errorMessage = 'Sorry, I couldn\'t connect to the server. Please check your connection.';
            
            if (error.message) {
                if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                    errorMessage = 'Network error. Please check your internet connection and try again.';
                } else if (error.message.includes('Invalid response')) {
                    errorMessage = 'Server returned an invalid response. Please try again.';
                }
            }
            
            this.addMessage('bot', errorMessage, null, null, null, null);
            console.error('Network error:', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    addMessage(role, content, pdfUrl = null, messageId = null, intent = null, userMessage = null) {
        if (!this.messagesContainer) {
            console.error('Chatbot messages container not found');
            return;
        }
        
        const isAssistant = role === 'bot' || role === 'assistant';
        const displayRole = isAssistant ? 'bot' : role;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${displayRole}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = displayRole === 'user' ? '👤' : '🤖';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const textContainer = document.createElement('div');
        textContainer.className = 'message-text';
        
        if (isAssistant && typeof marked !== 'undefined') {
            // Use marked.js for bot messages to render markdown
            // Sanitize by escaping script tags first
            const sanitized = content
                .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                .replace(/javascript:/gi, '');
            
            // Parse markdown
            let htmlContent = marked.parse(sanitized);
            
            // Add target="_blank" to all links for security
            htmlContent = htmlContent.replace(/<a /g, '<a target="_blank" rel="noopener noreferrer" ');
            
            textContainer.innerHTML = htmlContent;
        } else {
            // For user messages, escape HTML and convert newlines
            const escapedContent = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // Convert URLs to clickable links
            const urlRegex = /(https?:\/\/[^\s]+)/g;
            const contentWithLinks = escapedContent.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
            textContainer.innerHTML = contentWithLinks.replace(/\n/g, '<br>');
        }
        
        messageContent.appendChild(textContainer);
        
        // Add PDF link/embed if provided
        if (pdfUrl) {
            const pdfContainer = document.createElement('div');
            pdfContainer.className = 'pdf-container';
            pdfContainer.style.marginTop = '12px';
            pdfContainer.style.padding = '12px';
            pdfContainer.style.backgroundColor = '#f8f9fa';
            pdfContainer.style.borderRadius = '8px';
            pdfContainer.style.border = '1px solid #e0e0e0';
            
            // PDF Download/View Link
            const pdfLink = document.createElement('a');
            pdfLink.href = pdfUrl;
            pdfLink.target = '_blank';
            pdfLink.rel = 'noopener noreferrer';
            pdfLink.className = 'pdf-link';
            pdfLink.style.cssText = 'display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; background: #007bff; color: white; border-radius: 6px; text-decoration: none; font-weight: 500; transition: background 0.2s;';
            pdfLink.innerHTML = '📚 View Academic Handbook PDF';
            // Hover effect: darker blue on hover, return to original on mouseout
            pdfLink.onmouseover = function() { this.style.background = '#0056b3'; };
            pdfLink.onmouseout = function() { this.style.background = '#007bff'; };
            pdfContainer.appendChild(pdfLink);
            
            messageContent.appendChild(pdfContainer);
        }
        
        // Add feedback buttons for bot messages
        if (isAssistant) {
            const feedbackContainer = this.createFeedbackButtons(messageId, content, intent, userMessage);
            messageContent.appendChild(feedbackContainer);
        }
        
        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = this.formatTime(new Date());
        messageContent.appendChild(time);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    createFeedbackButtons(messageId, botResponse, intent, userMessage) {
        const feedbackContainer = document.createElement('div');
        feedbackContainer.className = 'feedback-buttons';
        feedbackContainer.style.cssText = `
            margin-top: 12px;
            padding: 10px 14px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: space-between;
        `;
        
        const label = document.createElement('span');
        label.textContent = 'Was this answer helpful?';
        label.style.cssText = 'font-size: 13px; color: #495057; font-weight: 500;';
        
        const buttonGroup = document.createElement('div');
        buttonGroup.style.cssText = 'display: flex; gap: 8px;';
        
        // Good button
        const goodButton = document.createElement('button');
        goodButton.innerHTML = '👍 Good';
        goodButton.style.cssText = `
            padding: 6px 16px;
            font-size: 13px;
            border: 1px solid #28a745;
            background: #28a745;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        `;
        goodButton.onmouseover = () => { goodButton.style.background = '#218838'; goodButton.style.transform = 'scale(1.05)'; };
        goodButton.onmouseout = () => { goodButton.style.background = '#28a745'; goodButton.style.transform = 'scale(1)'; };
        goodButton.onclick = () => this.submitFeedback(feedbackContainer, 'good', messageId, botResponse, intent, userMessage);
        
        // Bad button
        const badButton = document.createElement('button');
        badButton.innerHTML = '👎 Not Good';
        badButton.style.cssText = `
            padding: 6px 16px;
            font-size: 13px;
            border: 1px solid #dc3545;
            background: #dc3545;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        `;
        badButton.onmouseover = () => { badButton.style.background = '#c82333'; badButton.style.transform = 'scale(1.05)'; };
        badButton.onmouseout = () => { badButton.style.background = '#dc3545'; badButton.style.transform = 'scale(1)'; };
        badButton.onclick = () => this.submitFeedback(feedbackContainer, 'bad', messageId, botResponse, intent, userMessage);
        
        buttonGroup.appendChild(goodButton);
        buttonGroup.appendChild(badButton);
        feedbackContainer.appendChild(label);
        feedbackContainer.appendChild(buttonGroup);
        
        return feedbackContainer;
    }
    
    async submitFeedback(container, feedbackType, messageId, botResponse, intent, userMessage) {
        // Show thank you message immediately
        const isGood = feedbackType === 'good';
        container.innerHTML = '';
        container.style.cssText = `
            margin-top: 12px;
            padding: 8px 12px;
            font-size: 13px;
            color: ${isGood ? '#28a745' : '#dc3545'};
            background-color: ${isGood ? '#d4edda' : '#f8d7da'};
            border: 1px solid ${isGood ? '#c3e6cb' : '#f5c6cb'};
            border-radius: 6px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        `;
        container.innerHTML = `<span>✓</span><span>${isGood ? 'Thank you for your feedback!' : 'Thanks for helping us improve!'}</span>`;
        
        // Submit feedback to API
        try {
            await this.apiCall('/api/feedback/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message_id: messageId,
                    conversation_id: this.conversationId,
                    feedback_type: feedbackType,
                    user_message: userMessage || '',
                    bot_response: botResponse,
                    intent: intent,
                    session_id: this.sessionId
                })
            });
            console.log(`Feedback submitted: ${feedbackType}`);
        } catch (error) {
            console.error('Error submitting feedback:', error);
        }
    }
    
    showTyping() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'block';
        }
        this.scrollToBottom();
    }
    
    hideTyping() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        if (this.sendButton) {
            this.sendButton.disabled = loading;
        }
        if (this.input) {
            this.input.disabled = loading;
        }
        
        // Disable microphone button while loading to prevent starting
        // speech recognition during an active request (tests expect
        // mic to be disabled while loading)
        if (this.micButton) {
            this.micButton.disabled = loading;
        }
    }
    
    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }
    
    async loadConversationHistory() {
        if (!this.conversationId) {
            return;
        }
        
        try {
            const response = await this.apiCall(
                `/api/conversations/?conversation_id=${this.conversationId}`
            );
            
            if (response.ok) {
                let data;
                try {
                    data = await response.json();
                } catch (jsonError) {
                    console.error('Error parsing conversation history JSON:', jsonError);
                    return;
                }
                
                // Clear existing messages (except welcome)
                const welcomeMessage = this.messagesContainer.querySelector('.message');
                this.messagesContainer.innerHTML = '';
                if (welcomeMessage) {
                    this.messagesContainer.appendChild(welcomeMessage);
                }
                
                // Load messages
                if (data.messages && Array.isArray(data.messages) && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        if (msg.role !== 'system' && msg.content) {
                            this.addMessage(msg.role, msg.content, null, null, null, null);
                        }
                    });
                }
            } else if (response.status === 404) {
                console.warn('Conversation not found:', this.conversationId);
            } else {
                console.error('Error loading conversation history:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
            // Don't show error to user for history loading failures
        }
    }
    
    showBadge(count) {
        if (this.badge) {
            this.badge.textContent = count;
            this.badge.style.display = 'flex';
        }
    }
    
    hideBadge() {
        if (this.badge) {
            this.badge.style.display = 'none';
        }
    }
    
    async apiCall(url, options = {}) {
        // Get CSRF token if available
        const csrftoken = this.getCookie('csrftoken');
        if (csrftoken) {
            options.headers = options.headers || {};
            options.headers['X-CSRFToken'] = csrftoken;
        }

        // Prefix relative URLs with the backend base URL
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        return fetch(fullUrl, options);
    }
    
    getCookie(name) {
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
    }
    
    toggleSpeechRecognition() {
        if (!this.speechSupported || !this.recognition) {
            this.addMessage('bot', 'Speech recognition is not supported in your browser. Please use Chrome or Edge for voice input.', null, null, null, null);
            return;
        }
        
        if (this.isRecording) {
            this.stopSpeechRecognition();
        } else {
            this.startSpeechRecognition();
        }
    }
    
    startSpeechRecognition() {
        if (!this.recognition || this.isRecording || this.isLoading) {
            return;
        }
        
        try {
            // Clear input field
            if (this.input) {
                this.input.value = '';
            }
            this.recognition.start();
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.handleSpeechError('start-failed');
        }
    }
    
    stopSpeechRecognition() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
        }
    }
    
    handleSpeechResult(transcript) {
        if (!transcript || !transcript.trim()) {
            return;
        }
        
        // Set the input value with the transcribed text
        if (this.input) {
            this.input.value = transcript;
        }
        
        // Automatically send the message
        this.sendMessage();
    }
    
    handleSpeechError(error) {
        this.isRecording = false;
        this.updateMicButtonState('error');
        this.updateStatus('Online');
        
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
                // User stopped recording, no error message needed
                return;
            case 'start-failed':
                errorMessage = 'Failed to start speech recognition. Please try again.';
                break;
            default:
                console.error('Speech recognition error:', error);
        }
        
        // Show error message after a brief delay to avoid interrupting UI
        setTimeout(() => {
            this.updateMicButtonState('inactive');
            if (error !== 'aborted') {
                this.addMessage('bot', errorMessage, null, null, null, null);
            }
        }, 100);
    }
    
    updateMicButtonState(state) {
        if (!this.micButton) return;
        
        // Remove all state classes
        this.micButton.classList.remove('mic-inactive', 'mic-recording', 'mic-error');
        
        // Add appropriate state class
        switch (state) {
            case 'recording':
                this.micButton.classList.add('mic-recording');
                this.micButton.title = 'Stop recording';
                break;
            case 'error':
                this.micButton.classList.add('mic-error');
                this.micButton.title = 'Error - Click to try again';
                break;
            case 'inactive':
            default:
                this.micButton.classList.add('mic-inactive');
                this.micButton.title = 'Voice input';
                break;
        }
    }
    
    updateStatus(text) {
        if (this.status) {
            this.status.textContent = text;
        }
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Check if required elements exist before initializing
        const requiredElements = [
            'chatbot-toggle',
            'chatbot-container',
            'chatbot-messages',
            'chatbot-input',
            'chatbot-send'
        ];
        
        const missingElements = requiredElements.filter(id => !document.getElementById(id));
        
        if (missingElements.length > 0) {
            console.warn('Chatbot: Some required elements are missing:', missingElements);
            console.warn('Chatbot initialization skipped. Make sure all chatbot HTML elements are present.');
            return;
        }
        
        window.chatbot = new Chatbot();
    } catch (error) {
        console.error('Error initializing chatbot:', error);
    }
});

