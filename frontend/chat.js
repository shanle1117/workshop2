/**
 * Chatbot JavaScript for FAIX Chatbot
 * Handles real-time chat interaction with AJAX calls to Django API
 */

class Chatbot {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
        this.conversationId = null;
        this.isOpen = false;
        this.isLoading = false;
        
        this.initializeElements();
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
        this.typingIndicator = document.getElementById('chatbot-typing');
        this.status = document.getElementById('chatbot-status');
        this.badge = document.getElementById('chatbot-badge');
    }
    
    attachEventListeners() {
        // Toggle chatbot
        this.toggle.addEventListener('click', () => this.toggleChatbot());
        this.minimize.addEventListener('click', () => this.toggleChatbot());
        
        // Send message
        this.sendButton.addEventListener('click', () => this.sendMessage());
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
            this.container.style.display = 'flex';
            this.input.focus();
            this.hideBadge();
        } else {
            this.container.style.display = 'none';
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
        const message = this.input.value.trim();
        
        if (!message || this.isLoading) {
            return;
        }
        
        // Clear input
        this.input.value = '';
        this.input.style.height = 'auto';
        
        // Add user message to UI
        this.addMessage('user', message);
        
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
                }),
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Update session and conversation IDs
                if (data.session_id) {
                    this.sessionId = data.session_id;
                    localStorage.setItem('chatbot_session_id', this.sessionId);
                }
                if (data.conversation_id) {
                    this.conversationId = data.conversation_id;
                }
                
                // Add bot response to UI
                this.hideTyping();
                this.addMessage('bot', data.response);
                
            } else {
                const error = await response.json();
                this.hideTyping();
                this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
                console.error('Chat API error:', error);
            }
        } catch (error) {
            this.hideTyping();
            this.addMessage('bot', 'Sorry, I couldn\'t connect to the server. Please check your connection.');
            console.error('Network error:', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const text = document.createElement('p');
        text.textContent = content;
        messageContent.appendChild(text);
        
        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = this.formatTime(new Date());
        messageContent.appendChild(time);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    showTyping() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.typingIndicator.style.display = 'none';
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.input.disabled = loading;
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
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
                const data = await response.json();
                
                // Clear existing messages (except welcome)
                const welcomeMessage = this.messagesContainer.querySelector('.message');
                this.messagesContainer.innerHTML = '';
                if (welcomeMessage) {
                    this.messagesContainer.appendChild(welcomeMessage);
                }
                
                // Load messages
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        if (msg.role !== 'system') {
                            this.addMessage(msg.role, msg.content);
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
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
        
        return fetch(url, options);
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
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new Chatbot();
});

