document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtnPill');
    const micBtn = document.getElementById('micBtnPill');
    const newChatBtn = document.getElementById('newChatBtn');
    const menuBtn = document.getElementById('menuBtn');
    const sidebar = document.getElementById('sidebar');
    const refreshChatBtn = document.getElementById('refreshChatBtn');
    const themeToggleBtn = document.getElementById('themeToggleBtn');

    // --- Theme Management ---
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);

    themeToggleBtn?.addEventListener('click', () => {
        const theme = document.documentElement.getAttribute('data-theme');
        const newTheme = theme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });

    function updateThemeIcon(theme) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('i');
        if (theme === 'light') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    }

    let recognition;
    const synth = window.speechSynthesis;
    let voices = [];

    function loadVoices() {
        voices = synth.getVoices();
    }

    loadVoices();
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = loadVoices;
    }

    let lastUserQuestion = ''; // Declare lastUserQuestion here

    function speak(text, btn) {
        if (!text) return;
        
        if (synth.speaking) {
            const wasSpeakingThis = btn.classList.contains('active-speaking');
            synth.cancel();
            
            // If it was already speaking THIS message, we just stop.
            if (wasSpeakingThis) {
                return; 
            }
        }
        
        // Reset all speak buttons
        document.querySelectorAll('.speak-btn').forEach(b => {
            b.classList.remove('active-speaking');
            b.innerHTML = '<i class="fas fa-volume-up"></i>';
        });

        const utterance = new SpeechSynthesisUtterance(text);
        
        // Try to find a friendly, natural sounding voice
        const preferredVoices = [
            "Google US English",
            "Microsoft Aria Online",
            "Microsoft Zira",
            "Microsoft Samantha",
            "Samantha",
            "Alex"
        ];
        
        let selectedVoice = null;
        for (let name of preferredVoices) {
            selectedVoice = voices.find(v => v.name.includes(name));
            if (selectedVoice) break;
        }

        if (!selectedVoice) {
            selectedVoice = voices.find(v => v.lang.startsWith('en'));
        }

        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }

        // Adjust for a friendlier tone
        utterance.pitch = 1.1; // Slightly higher pitch for friendliness
        utterance.rate = 1.0;  // Normal rate
        utterance.volume = 1.0;
        
        utterance.onstart = () => {
            btn.classList.add('active-speaking');
            btn.innerHTML = '<i class="fas fa-stop"></i>';
        };
        
        utterance.onend = () => {
            btn.classList.remove('active-speaking');
            btn.innerHTML = '<i class="fas fa-volume-up"></i>';
        };

        synth.speak(utterance);
    }

    // --- Speech Recognition Setup ---
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            micBtn.classList.add('active');
            micBtn.style.color = '#ef4444';
        };

        recognition.onend = () => {
            micBtn.classList.remove('active');
            micBtn.style.color = '';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            userInput.dispatchEvent(new Event('input'));
            sendQuestion();
        };
    }

    micBtn.addEventListener('click', () => {
        if (recognition) {
            recognition.start();
        } else {
            alert("Speech recognition not supported in this browser.");
        }
    });

    function updateGreeting() {
        const hour = new Date().getHours();
        const greetingElement = document.getElementById('timeGreeting');
        if (!greetingElement) return;

        let greeting = "Good Evening";
        if (hour < 12) greeting = "Good Morning";
        else if (hour < 17) greeting = "Good Afternoon";
        
        greetingElement.innerText = greeting;
    }
    updateGreeting();

    // --- UI Helpers ---
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    function appendMessage(role, text, isTyping = false) {
        // Hide welcome screen when first message is sent
        if (welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
            chatContainer.style.display = 'block';
        }

        const row = document.createElement('div');
        row.className = `message-row ${role}`;
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.innerHTML = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-star"></i>';
        
        const textBlock = document.createElement('div');
        textBlock.className = `text-block ${isTyping ? 'typing' : ''}`;
        
        if (!isTyping) {
            textBlock.innerText = text;
        }

        content.appendChild(avatar);
        content.appendChild(textBlock);
        row.appendChild(content);
        chatContainer.appendChild(row);

        if (role === 'ai' && !isTyping) {
            addMessageActions(textBlock, text);
        }

        chatContainer.scrollTop = chatContainer.scrollHeight;
        return textBlock;
    }

    function addMessageActions(container, text) {
        const actions = document.createElement('div');
        actions.className = 'actions';
        actions.innerHTML = `
            <button class="action-btn speak-btn" title="Listen"><i class="fas fa-volume-up"></i></button>
            <button class="action-btn" title="Like"><i class="far fa-thumbs-up"></i></button>
            <button class="action-btn" title="Dislike"><i class="far fa-thumbs-down"></i></button>
            <button class="action-btn regenerate" title="Regenerate"><i class="fas fa-redo"></i></button>
            <button class="action-btn copy" title="Copy"><i class="far fa-copy"></i></button>
        `;

        actions.querySelector('.speak-btn').addEventListener('click', function() {
            speak(text, this);
        });

        actions.querySelector('.copy').addEventListener('click', () => {
            navigator.clipboard.writeText(text);
            const icon = actions.querySelector('.copy i');
            icon.className = 'fas fa-check';
            setTimeout(() => { icon.className = 'far fa-copy'; }, 2000);
        });

        actions.querySelector('.regenerate').addEventListener('click', () => {
            if (lastUserQuestion) {
                userInput.value = lastUserQuestion;
                sendQuestion();
            }
        });

        container.appendChild(actions);
    }

    async function typeWriter(element, text) {
        element.classList.add('typing');
        let i = 0;
        element.innerText = '';
        
        return new Promise(resolve => {
            function type() {
                if (i < text.length) {
                    element.innerText += text.charAt(i);
                    i++;
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    setTimeout(type, 15);
                } else {
                    element.classList.remove('typing');
                    addMessageActions(element, text);
                    resolve();
                }
            }
            type();
        });
    }

    let currentSessionId = typeof CURRENT_SESSION_ID !== 'undefined' ? CURRENT_SESSION_ID : '';

    async function sendQuestion() {
        const question = userInput.value.trim();
        if (!question) return;

        lastUserQuestion = question;
        appendMessage('user', question);
        
        userInput.value = '';
        userInput.style.height = 'auto';

        const thinking = document.createElement('div');
        thinking.className = 'message-row ai';
        thinking.innerHTML = `
            <div class="message-content">
                <div class="avatar"><i class="fas fa-star"></i></div>
                <div class="text-block typing">CelestAI is thinking...</div>
            </div>
        `;
        chatContainer.appendChild(thinking);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const response = await fetch('/ask/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, session_id: currentSessionId })
            });
            const data = await response.json();
            
            thinking.remove();
            const aiTextElement = appendMessage('ai', '', true);
            await typeWriter(aiTextElement, data.answer);

            // If a new session was created, update the URL and currentSessionId
            if (data.session_id && currentSessionId !== data.session_id) {
                currentSessionId = data.session_id;
                const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?session=' + currentSessionId;
                window.history.pushState({ path: newUrl }, '', newUrl);
                
                // Reload after a short delay to let the user see the AI started responding,
                // this ensures the sidebar gets the new title.
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }

            if (data.redirect) {
                // Show alert then redirect immediately after user clicks OK
                alert("Please login to save your chat progress and continue the conversation!");
                window.location.href = data.redirect;
            }

        } catch (error) {
            thinking.remove();
            appendMessage('ai', 'Sorry, I encountered an error. Please try again.');
        }
    }

    // Suggested actions
    document.querySelectorAll('.suggest-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            userInput.value = btn.innerText.trim();
            userInput.dispatchEvent(new Event('input'));
            sendQuestion();
        });
    });

    // --- Listeners ---
    sendBtn.addEventListener('click', sendQuestion);

    refreshChatBtn?.addEventListener('click', async () => {
        if (confirm("Reset current chat history?")) {
            await fetch('/reset/', { method: 'POST' });
            window.location.reload();
        }
    });

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });

    newChatBtn.addEventListener('click', () => {
        // Just navigate to the index page without a session parameter to start a fresh chat
        window.location.href = '/';
    });

    menuBtn?.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // --- Session Menu & Deletion ---
    document.querySelectorAll('.session-menu-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const sid = btn.getAttribute('data-session-id');
            const dropdown = document.getElementById(`dropdown-${sid}`);
            
            // Close all other dropdowns first
            document.querySelectorAll('.session-dropdown').forEach(d => {
                if (d !== dropdown) d.style.display = 'none';
            });

            // Toggle current dropdown
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
        });
    });

    document.querySelectorAll('.delete-session-item').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const sid = btn.getAttribute('data-session-id');
            if (confirm("Are you sure you want to delete this chat session?")) {
                try {
                    const response = await fetch(`/delete-session/?session_id=${sid}`);
                    const data = await response.json();
                    if (response.ok) {
                        // If we are currently viewing this session, redirect to home
                        if (CURRENT_SESSION_ID === sid) {
                            window.location.href = '/';
                        } else {
                            window.location.reload();
                        }
                    } else {
                        alert("Error deleting session: " + data.error);
                    }
                } catch (err) {
                    alert("Failed to delete session.");
                }
            }
        });
    });

    // Close dropdowns on click outside (mobile)
    document.addEventListener('click', (e) => {
        // Close session dropdowns
        if (!e.target.closest('.session-menu-btn') && !e.target.closest('.session-dropdown')) {
            document.querySelectorAll('.session-dropdown').forEach(d => d.style.display = 'none');
        }

        if (window.innerWidth <= 768 && 
            !sidebar.contains(e.target) && 
            !menuBtn.contains(e.target) && 
            sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    });

    // --- Initialize Full History ---
    if (typeof FULL_HISTORY !== 'undefined' && FULL_HISTORY.length > 0) {
        FULL_HISTORY.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });
    }
});
