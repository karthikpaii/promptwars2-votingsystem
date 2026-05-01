document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const quickReplies = document.getElementById('quick-replies');

    // Voice Guidance State
    let voiceEnabled = false;
    const voiceToggleBtn = document.getElementById('voice-toggle-btn');

    voiceToggleBtn.addEventListener('click', () => {
        voiceEnabled = !voiceEnabled;
        voiceToggleBtn.style.background = voiceEnabled ? '#2563eb' : 'rgba(255,255,255,0.2)';
        voiceToggleBtn.setAttribute('aria-pressed', voiceEnabled.toString());
        if (voiceEnabled) speakText("Voice guidance enabled.");
        else window.speechSynthesis.cancel();
    });

    // Session ID
    let sessionId = sessionStorage.getItem('electionAssistantSessionId');
    if (!sessionId) {
        sessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);
        sessionStorage.setItem('electionAssistantSessionId', sessionId);
    }

    // Static quick reply buttons (initial state only)
    document.querySelectorAll('.quick-reply-btn').forEach(btn => {
        btn.addEventListener('click', () => handleUserMessage(btn.textContent.trim()));
    });

    // Form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (text) handleUserMessage(text);
    });

    async function handleUserMessage(message) {
        if (!message) return;

        // Remove any existing dynamic action buttons
        clearDynamicActions();

        // Hide initial quick replies once conversation starts
        if (quickReplies) quickReplies.style.display = 'none';

        // Disable input
        setInputEnabled(false);
        addMessage(message, 'user');
        chatInput.value = '';

        const typingId = showTypingIndicator();

        try {
            const userLocation = document.getElementById('user-location').value;
            const userLanguage = document.getElementById('user-language')?.value || 'English';

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    session_id: sessionId,
                    location: userLocation,
                    language: userLanguage,
                }),
            });

            const data = await response.json();
            removeTypingIndicator(typingId);

            if (data.status === 'success') {
                const isWarning = data.message.startsWith('WARNING:');
                addMessage(data.message, isWarning ? 'warning' : 'assistant');
                speakText(data.message);

                // Render dynamic action buttons from backend
                if (!isWarning && data.suggested_actions && data.suggested_actions.length > 0) {
                    renderDynamicActions(data.suggested_actions);
                }

                // Show timeline if relevant
                if (message.toLowerCase().includes('timeline') || data.message.toLowerCase().includes('timeline')) {
                    document.getElementById('timeline-container')?.classList.remove('hidden');
                }
            } else {
                addMessage('Sorry, I encountered an error. Please try again.', 'warning');
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            addMessage('Network error. Please check your connection.', 'warning');
        } finally {
            setInputEnabled(true);
            chatInput.focus();
        }
    }

    function renderDynamicActions(actions) {
        const container = document.createElement('div');
        container.className = 'dynamic-actions';
        container.setAttribute('role', 'group');
        container.setAttribute('aria-label', 'Suggested actions');

        actions.forEach(actionText => {
            const btn = document.createElement('button');
            btn.className = 'dynamic-action-btn';
            btn.textContent = actionText;
            btn.type = 'button';
            btn.addEventListener('click', () => {
                clearDynamicActions();
                handleUserMessage(actionText);
            });
            container.appendChild(btn);
        });

        chatMessages.appendChild(container);
        scrollToBottom();
    }

    function clearDynamicActions() {
        document.querySelectorAll('.dynamic-actions').forEach(el => el.remove());
    }

    function setInputEnabled(enabled) {
        chatInput.disabled = !enabled;
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.disabled = !enabled;
            sendBtn.style.opacity = enabled ? '1' : '0.5';
        }
    }

    // --- Notification Modal ---
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

    closeModalBtn.addEventListener('click', () => { notifyModal.style.display = 'none'; });

    notifyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('notify-email').value;
        const location = document.getElementById('user-location').value;
        try {
            const response = await fetch('/api/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, location }),
            });
            const data = await response.json();
            notifyStatus.style.display = 'block';
            if (data.status === 'success') {
                notifyStatus.textContent = 'Successfully subscribed to alerts!';
                notifyStatus.style.color = '#16a34a';
                setTimeout(() => { notifyModal.style.display = 'none'; }, 2000);
            } else {
                notifyStatus.textContent = 'Error subscribing. Try again.';
                notifyStatus.style.color = '#ef4444';
            }
        } catch {
            notifyStatus.style.display = 'block';
            notifyStatus.textContent = 'Network error.';
            notifyStatus.style.color = '#ef4444';
        }
    });

    // --- Message Rendering ---
    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = 'message';
        if (sender === 'user') div.classList.add('user-message');
        else if (sender === 'assistant') div.classList.add('assistant-message');
        else if (sender === 'warning') div.classList.add('assistant-message', 'warning-message');

        // Format: line breaks, bold, numbered lists
        let formatted = text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        div.innerHTML = `<p>${formatted}</p>`;
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'typing-indicator';
        div.setAttribute('aria-label', 'Assistant is typing');
        div.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
        chatMessages.appendChild(div);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        document.getElementById(id)?.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function speakText(text) {
        if (!voiceEnabled || !('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();
        const clean = text.replace(/\*\*(.*?)\*\*/g, '$1').replace(/<[^>]*>/gm, '');
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.rate = 0.9;
        const lang = document.getElementById('user-language')?.value || 'English';
        const langMap = { Hindi: 'hi-IN', Kannada: 'kn-IN', Bengali: 'bn-IN', Telugu: 'te-IN', Marathi: 'mr-IN', Tamil: 'ta-IN' };
        utterance.lang = langMap[lang] || 'en-US';
        window.speechSynthesis.speak(utterance);
    }
});
