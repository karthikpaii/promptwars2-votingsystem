document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const quickReplies = document.querySelectorAll('.quick-reply-btn');

    // Voice Guidance State
    let voiceEnabled = false;
    const voiceToggleBtn = document.getElementById('voice-toggle-btn');
    const voiceIcon = document.getElementById('voice-icon');

    voiceToggleBtn.addEventListener('click', () => {
        voiceEnabled = !voiceEnabled;
        if (voiceEnabled) {
            voiceToggleBtn.style.background = '#2563eb'; // Blue when active
            voiceToggleBtn.setAttribute('aria-pressed', 'true');
            speakText("Voice guidance enabled. I will read my answers to you.");
        } else {
            voiceToggleBtn.style.background = 'rgba(255, 255, 255, 0.2)';
            voiceToggleBtn.setAttribute('aria-pressed', 'false');
            window.speechSynthesis.cancel(); // Stop speaking if turned off
        }
    });

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
        }
    });

    // Session ID to keep track of the chat context
    let sessionId = sessionStorage.getItem('electionAssistantSessionId');
    if (!sessionId) {
        sessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);
        sessionStorage.setItem('electionAssistantSessionId', sessionId);
    }

    async function handleUserMessage(message) {
        if (!message) return;

        // Disable input to prevent double submission
        chatInput.disabled = true;
        const sendBtn = document.getElementById('send-btn');
        if(sendBtn) {
            sendBtn.disabled = true;
            sendBtn.style.opacity = '0.5';
        }

        // Add user message to UI
        addMessage(message, 'user');
        chatInput.value = '';

        // Show typing indicator
        const typingId = showTypingIndicator();

        try {
            const userLocation = document.getElementById('user-location').value;
            const userLanguage = document.getElementById('user-language').value;
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message, 
                    session_id: sessionId,
                    location: userLocation,
                    language: userLanguage
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            removeTypingIndicator(typingId);

            if (data.status === 'success') {
                // Check if it's a warning message
                const isWarning = data.message.startsWith('WARNING:');
                addMessage(data.message, isWarning ? 'warning' : 'assistant');
                
                // Speak the message if voice is enabled
                speakText(data.message);
                
                // Show timeline if the topic is timeline/dates
                if (message.toLowerCase().includes('timeline') || message.toLowerCase().includes('date') || data.message.toLowerCase().includes('timeline')) {
                    document.getElementById('timeline-container').classList.remove('hidden');
                }
            } else {
                addMessage("Sorry, I encountered an error. Please try again.", 'warning');
                speakText("Sorry, I encountered an error. Please try again.");
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            addMessage("Network error. Please check your connection.", 'warning');
            speakText("Network error. Please check your connection.");
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            if(sendBtn) {
                sendBtn.disabled = false;
                sendBtn.style.opacity = '1';
            }
            chatInput.focus();
        }
    }

    // --- Notification Modal Logic ---
    const notifyBtn = document.getElementById('notify-btn');
    const notifyModal = document.getElementById('notify-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const notifyForm = document.getElementById('notify-form');
    const notifyStatus = document.getElementById('notify-status');

    notifyBtn.addEventListener('click', () => {
        notifyModal.style.display = 'flex';
        notifyStatus.style.display = 'none';
        document.getElementById('notify-email').value = '';
    });

    closeModalBtn.addEventListener('click', () => {
        notifyModal.style.display = 'none';
    });

    notifyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('notify-email').value;
        const location = document.getElementById('user-location').value;

        try {
            const response = await fetch('/api/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, location })
            });
            const data = await response.json();
            
            if(data.status === 'success') {
                notifyStatus.style.display = 'block';
                notifyStatus.textContent = 'Successfully subscribed to alerts!';
                notifyStatus.style.color = '#16a34a';
                setTimeout(() => { notifyModal.style.display = 'none'; }, 2000);
            } else {
                notifyStatus.style.display = 'block';
                notifyStatus.textContent = 'Error subscribing. Try again.';
                notifyStatus.style.color = '#ef4444';
            }
        } catch (error) {
            notifyStatus.style.display = 'block';
            notifyStatus.textContent = 'Network error.';
            notifyStatus.style.color = '#ef4444';
        }
    });

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

    // Text to Speech Function
    function speakText(text) {
        if (!voiceEnabled || !('speechSynthesis' in window)) return;
        
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();
        
        // Strip markdown and HTML for cleaner speech
        const cleanText = text.replace(/\*\*(.*?)\*\*/g, '$1')
                             .replace(/<[^>]*>?/gm, '')
                             .replace(/Step \d+:/g, (match) => match + " "); 

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 0.9; // Slightly slower for better comprehension
        utterance.pitch = 1;
        
        // Try to use a natural English voice if available
        const voices = window.speechSynthesis.getVoices();
        const englishVoice = voices.find(voice => voice.lang.includes('en-') && voice.name.includes('Natural'));
        if(englishVoice) utterance.voice = englishVoice;

        window.speechSynthesis.speak(utterance);
    }
});
