document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const quickReplies = document.querySelectorAll('.quick-reply-btn');

    // Handle Quick Replies
    quickReplies.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.textContent;
            handleUserMessage(text);
        });
    });

    // Handle Form Submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (text) {
            handleUserMessage(text);
            chatInput.value = '';
        }
    });

    // Session ID to keep track of the chat context
    let sessionId = sessionStorage.getItem('electionAssistantSessionId');
    if (!sessionId) {
        sessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);
        sessionStorage.setItem('electionAssistantSessionId', sessionId);
    }

    async function handleUserMessage(message) {
        // Add user message to UI
        addMessage(message, 'user');
        
        // Show typing indicator
        const typingId = showTypingIndicator();

        try {
            const userLocation = document.getElementById('user-location').value;
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message, 
                    session_id: sessionId,
                    location: userLocation
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            removeTypingIndicator(typingId);

            if (data.status === 'success') {
                // Check if it's a warning message
                const isWarning = data.message.startsWith('WARNING:');
                addMessage(data.message, isWarning ? 'warning' : 'assistant');
                
                // Show timeline if the topic is timeline/dates
                if (message.toLowerCase().includes('timeline') || message.toLowerCase().includes('date') || data.message.toLowerCase().includes('timeline')) {
                    document.getElementById('timeline-container').classList.remove('hidden');
                }
            } else {
                addMessage("Sorry, I encountered an error. Please try again.", 'warning');
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            addMessage("Network error. Please check your connection.", 'warning');
        }
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        
        // Base classes
        div.className = 'message';
        
        // Sender specific classes
        if (sender === 'user') div.classList.add('user-message');
        else if (sender === 'assistant') div.classList.add('assistant-message');
        else if (sender === 'warning') {
            div.classList.add('assistant-message', 'warning-message');
        }

        // Simple formatting for line breaks and bold text
        let formattedText = text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        div.innerHTML = `<p>${formattedText}</p>`;
        
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'typing-indicator';
        div.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        chatMessages.appendChild(div);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
