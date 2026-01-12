import React from 'react';
import ReactDOM from 'react-dom/client';
import Chatbot from './Chatbot';

// Initialize React Chatbot
const root = document.getElementById('chatbot-root');
if (root) {
  const reactRoot = ReactDOM.createRoot(root);
  reactRoot.render(<Chatbot />);
}

