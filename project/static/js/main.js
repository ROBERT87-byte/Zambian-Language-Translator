document.addEventListener('DOMContentLoaded', () => {

    // --- Settings Menu Toggle Logic ---
    const settingsBtn = document.querySelector('.settings-btn');
    const settingsMenu = document.getElementById('settingsMenu');
    
    if (settingsBtn && settingsMenu) {
        settingsBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            const isVisible = settingsMenu.style.display === 'block';
            settingsMenu.style.display = isVisible ? 'none' : 'block';
        });

        // Close the menu if clicked outside
        document.addEventListener('click', (event) => {
            if (!settingsMenu.contains(event.target) && !settingsBtn.contains(event.target)) {
                settingsMenu.style.display = 'none';
            }
        });
    }

    // --- Dark Mode Logic ---
    const darkToggle = document.getElementById('darkModeToggle');
    const darkModeEnabled = localStorage.getItem('darkMode') === 'enabled';

    if (darkToggle) {
        if (darkModeEnabled) {
            document.body.classList.add('dark-mode');
            darkToggle.checked = true;
        }

        darkToggle.addEventListener('change', () => {
            if (darkToggle.checked) {
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'enabled');
            } else {
                document.body.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'disabled');
            }
        });
    }

    // --- Translation Logic ---
    async function translateText() {
        const english = document.getElementById('english_text').value;
        const outputBox = document.getElementById('output');
        
        const languageSelector = document.getElementById('language_selector');
        const currentLanguage = languageSelector.value;

        if (!english.trim()) {
            outputBox.innerText = 'Please enter some English text.';
            return;
        }

        if (!currentLanguage) {
            outputBox.innerText = 'Please select a language to translate to.';
            return;
        }

        outputBox.innerText = 'Translating...';

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: english, lang: currentLanguage })
            });

            const result = await response.json();

            if (!response.ok) {
                outputBox.innerText = `❌ Server Error: ${result.translation || 'Something went wrong on the server.'}`;
                return;
            }

            if (result.translation) {
                outputBox.innerText = result.translation;
            } else if (result.message) {
                outputBox.innerHTML = `
                    ❌ <strong>${result.message}</strong><br>
                    💡 ${result.suggestion}
                `;
            } else {
                outputBox.innerText = 'An unknown error occurred. Please try again.';
            }

        } catch (err) {
            outputBox.innerText = 'Error connecting to server. Please check your internet connection and ensure the server is running.';
            console.error("Network or parsing error:", err);
        }
    }

    // --- Speech Synthesis ---
    function speakTranslation() {
        const text = document.getElementById('output').innerText;
        if (!text || text === 'Translation will appear here') {
            alert('Please translate something first.');
            return;
        }
        const languageSelector = document.getElementById('language_selector');
        const currentLanguageCode = languageSelector.value;

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = `en-${currentLanguageCode}`;
        utterance.rate = 0.9;
        speechSynthesis.speak(utterance);
    }

    // --- Download Translation ---
    function downloadTranslation() {
        const translation = document.getElementById('output').innerText;
        if (!translation || translation === 'Translation will appear here') {
            alert('Please translate something first.');
            return;
        }
        const languageSelector = document.getElementById('language_selector');
        const currentLanguage = languageSelector.value;

        const blob = new Blob([translation], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `translation_${currentLanguage}.txt`;
        link.click();
    }

    // --- Speech Recognition ---
    const micBtn = document.getElementById('micBtn');
    const englishInput = document.getElementById('english_text');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        micBtn.addEventListener('click', () => {
            micBtn.innerHTML = '<i class="fas fa-microphone-slash"></i> Listening...';
            recognition.start();
        });
        recognition.onresult = (e) => {
            englishInput.value = e.results[0][0].transcript;
            translateText();
            micBtn.innerHTML = '<i class="fas fa-microphone"></i> Speak';
        };
        recognition.onend = () => {
            micBtn.innerHTML = '<i class="fas fa-microphone"></i> Speak';
        };
        recognition.onerror = (e) => {
            console.error('Speech recognition error:', e.error);
            micBtn.innerHTML = '<i class="fas fa-microphone"></i> Speak';
        };
    } else {
        if (micBtn) micBtn.style.display = 'none';
    }

    // --- Contribution Form Logic ---
    const contributionForm = document.getElementById("contributionForm");
    if (contributionForm) {
        contributionForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            const english = document.getElementById("contrib_english").value.trim();
            const translated = document.getElementById("contrib_translation").value.trim();
            
            const languageSelector = document.getElementById('contrib_language_selector');
            const language = languageSelector.value;
            
            const messageBox = document.getElementById("contribMessage");

            if (!english || !translated || !language) {
                messageBox.style.color = "red";
                messageBox.innerText = "⚠️ Please fill in all fields and select a language.";
                return;
            }

            const csrfToken = document.querySelector('input[name="csrf_token"]').value;

            try {
                const res = await fetch("/contribute", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({ english, translation: translated, language })
                });

                const data = await res.json();

                if (res.ok) {
                    messageBox.style.color = "green";
                    messageBox.innerText = "✅ Contribution submitted successfully!";
                    document.getElementById("contrib_english").value = "";
                    document.getElementById("contrib_translation").value = "";
                    document.getElementById("contrib_language_selector").value = "";
                } else {
                    messageBox.style.color = "red";
                    messageBox.innerText = `❌ Error: ${data.message || 'Something went wrong.'}`;
                }
            } catch (error) {
                messageBox.style.color = "red";
                messageBox.innerText = "❌ An error occurred. Please check your connection.";
            }
        });
    }

    // --- Event Listeners for Forms and Buttons ---
    const translationForm = document.getElementById('translationForm');
    if (translationForm) {
        translationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            translateText();
        });
    }

    const listenButton = document.getElementById('listenBtn');
    if (listenButton) {
        listenButton.addEventListener('click', speakTranslation);
    }
    
    const downloadButton = document.getElementById('downloadBtn');
    if (downloadButton) {
        downloadButton.addEventListener('click', downloadTranslation);
    }
});