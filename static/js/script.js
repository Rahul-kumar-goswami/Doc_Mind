document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeScreen = document.getElementById('welcome-screen');
    const newChatBtn = document.getElementById('new-chat-btn');
    const historyList = document.getElementById('history-list');
    
    const mainMicBtn = document.getElementById('main-mic-btn');
    const micCard = document.querySelector('.mic-card');
    const waveform = document.getElementById('waveform');
    const micStatusText = document.getElementById('mic-status-text');

    const aiTemplate = document.getElementById('ai-message-template');
    const userTemplate = document.getElementById('user-message-template');

    // State
    let currentSessionId = window.CURRENT_SESSION_ID || null;
    const chatHistory = window.CHAT_HISTORY || [];

    // Initialize Markdown
    marked.setOptions({
        headerIds: false,
        mangle: false,
        breaks: true,
        highlight: function(code, lang) {
            return code; // Simplified for now, could add Prism.js later
        }
    });

    // --- Core Functions ---

    function createMessageElement(content, role) {
        const template = role === 'user' ? userTemplate : aiTemplate;
        const clone = template.content.cloneNode(true);
        const msgDiv = clone.querySelector('.message');
        const contentDiv = clone.querySelector('.message-content');

        if (role === 'ai') {
            contentDiv.innerHTML = marked.parse(content);
            // Attach actions
            const likeBtn = clone.querySelector('button[title="Like"]');
            const dislikeBtn = clone.querySelector('button[title="Dislike"]');
            
            const feedbackToast = (text) => Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'success',
                title: text,
                showConfirmButton: false,
                timer: 1500,
                background: '#111827',
                color: '#fff'
            });

            if (likeBtn) likeBtn.addEventListener('click', () => feedbackToast('Thanks for your feedback!'));
            if (dislikeBtn) dislikeBtn.addEventListener('click', () => feedbackToast('Sorry about that. We will improve.'));

            const copyBtn = clone.querySelector('.copy-msg');
            if (copyBtn) {
                copyBtn.addEventListener('click', () => {
                    navigator.clipboard.writeText(content);
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: 'Copied to clipboard',
                        showConfirmButton: false,
                        timer: 1500,
                        background: '#111827',
                        color: '#fff'
                    });
                });
            }
            const regenBtn = clone.querySelector('.regenerate-msg');
            if (regenBtn) {
                regenBtn.addEventListener('click', () => {
                    const lastUserMsg = [...chatMessages.querySelectorAll('.message.user')].pop();
                    if (lastUserMsg) {
                        const text = lastUserMsg.querySelector('.message-content').innerText;
                        sendMessage(text);
                    }
                });
            }
        } else {
            contentDiv.innerText = content;
        }

        return msgDiv;
    }

    function addMessageToUI(content, role, animate = true) {
        if (welcomeScreen) welcomeScreen.style.display = 'none';
        
        const msgEl = createMessageElement(content, role);
        if (!animate) msgEl.style.animation = 'none';
        
        chatMessages.appendChild(msgEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'message ai typing-indicator';
        div.id = 'typing-indicator';
        div.innerHTML = `
            <div class="message-avatar"><i class='bx bxs-bot'></i></div>
            <div class="message-wrapper">
                <div class="message-content">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    let isProcessing = false;

    async function sendMessage(text) {
        if (!text || isProcessing) return;

        isProcessing = true;
        chatInput.disabled = true;
        sendBtn.disabled = true;
        sendBtn.classList.remove('active');

        addMessageToUI(text, 'user');
        chatInput.value = '';
        chatInput.style.height = 'auto';

        showTypingIndicator();

        try {
            const response = await fetch('/ask/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: text,
                    session_id: currentSessionId
                })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (data.answer) {
                addMessageToUI(data.answer, 'ai');

                // Handle Guest Redirect (One-free-chat flow)
                if (data.redirect) {
                    setTimeout(() => {
                        Swal.fire({
                            title: 'Login to Continue',
                            text: 'You have used your free guest query. Please login or sign up to continue the conversation and access the full dashboard.',
                            icon: 'info',
                            showCancelButton: true,
                            confirmButtonText: 'Login / Sign Up',
                            cancelButtonText: 'Stay here',
                            background: '#111827',
                            color: '#fff',
                            confirmButtonColor: '#8b5cf6'
                        }).then((result) => {
                            isProcessing = false;
                            chatInput.disabled = false;
                            sendBtn.disabled = false;
                            if (result.isConfirmed) {
                                window.location.href = data.redirect;
                            }
                        });
                    }, 2000);
                    return;
                }

                if (data.session_id && !current_session_id) {
                    currentSessionId = data.session_id;
                    updateUrl(currentSessionId);
                    // Refresh history sidebar
                    setTimeout(() => window.location.reload(), 1000);
                    // Keep disabled during reload
                    return;
                }
            } else {
                addMessageToUI("I'm sorry, I encountered an issue.", 'ai');
            }
        } catch (error) {
            removeTypingIndicator();
            // Only show error if not aborted by page reload
            if (error.name !== 'AbortError') {
                addMessageToUI("Error: Could not connect to server. Please check your connection.", 'ai');
            }
        } finally {
            if (!current_session_id || window.location.search.includes('session=')) {
                isProcessing = false;
                chatInput.disabled = false;
                sendBtn.disabled = false;
            }
        }
    }


    function updateUrl(sessionId) {
        const newurl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?session=' + sessionId;
        window.history.pushState({path:newurl},'',newurl);
    }

    // --- Event Listeners ---

    // Auto-resize input
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value.trim() !== "") {
            sendBtn.classList.add('active');
        } else {
            sendBtn.classList.remove('active');
        }
    });

    sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(chatInput.value.trim());
        }
    });

    newChatBtn.addEventListener('click', () => {
        window.location.href = '/';
    });

    // History Item Actions
    document.querySelectorAll('.action-trigger').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Close other dropdowns
            document.querySelectorAll('.action-dropdown').forEach(d => {
                if (d !== trigger.nextElementSibling) d.classList.remove('show');
            });
            trigger.nextElementSibling.classList.toggle('show');
        });
    });

    // Global click to close dropdowns
    document.addEventListener('click', () => {
        document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('show'));
    });

    // Delete Chat
    document.querySelectorAll('.delete-chat').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const wrapper = btn.closest('.history-item-wrapper');
            const sessionId = wrapper.dataset.sessionId;

            const result = await Swal.fire({
                title: 'Delete Chat?',
                text: "This action cannot be undone.",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Yes, delete it!',
                cancelButtonText: 'Cancel'
            });

            if (result.isConfirmed) {
                try {
                    const response = await fetch('/delete-session/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId })
                    });
                    if (response.ok) {
                        wrapper.remove();
                        if (currentSessionId === sessionId) window.location.href = '/';
                    }
                } catch (err) {
                    console.error("Delete failed", err);
                }
            }
        });
    });

    // Rename Chat
    document.querySelectorAll('.rename-chat').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const wrapper = btn.closest('.history-item-wrapper');
            const sessionId = wrapper.dataset.sessionId;
            const currentTitle = wrapper.querySelector('.chat-title').innerText;

            const { value: newTitle } = await Swal.fire({
                title: 'Rename Chat',
                input: 'text',
                inputValue: currentTitle,
                showCancelButton: true,
                inputValidator: (value) => {
                    if (!value) return 'You need to write something!'
                }
            });

            if (newTitle && newTitle !== currentTitle) {
                try {
                    const response = await fetch('/rename-session/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId, title: newTitle })
                    });
                    if (response.ok) {
                        wrapper.querySelector('.chat-title').innerText = newTitle;
                    }
                } catch (err) {
                    console.error("Rename failed", err);
                }
            }
        });
    });

    // Suggestion Cards
    document.querySelectorAll('.suggestion-card').forEach(card => {
        card.addEventListener('click', () => {
            const text = card.querySelector('span').innerText;
            sendMessage(text);
        });
    });

    // Voice Recognition
    let isListening = false;
    let recognition;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isListening = true;
            micCard.classList.add('mic-active');
            waveform.classList.remove('hidden');
            micStatusText.innerText = 'Listening...';
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript;
                else interimTranscript += event.results[i][0].transcript;
            }
            if (finalTranscript) {
                micStatusText.innerText = 'Processing...';
                sendMessage(finalTranscript);
            } else if (interimTranscript) {
                micStatusText.innerText = interimTranscript;
            }
        };

        recognition.onend = () => {
            isListening = false;
            micCard.classList.remove('mic-active');
            waveform.classList.add('hidden');
            if (micStatusText.innerText === 'Listening...') micStatusText.innerText = 'Click to start conversation';
        };
    }

    mainMicBtn.addEventListener('click', () => {
        if (!recognition) {
            Swal.fire('Error', 'Speech recognition not supported in this browser.', 'error');
            return;
        }
        isListening ? recognition.stop() : recognition.start();
    });

    document.querySelectorAll('.voice-suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
            const text = item.querySelector('span').innerText.replace(/"/g, '');
            sendMessage(text);
        });
    });

    // Load initial history
    if (chatHistory && chatHistory.length > 0) {
        chatHistory.forEach(msg => addMessageToUI(msg.content, msg.role, false));
    }
});