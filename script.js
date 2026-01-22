// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', () => {
    // Get references to the HTML elements
    const chatSelector = document.getElementById('chat-selector');
    const messagesDiv = document.getElementById('messages');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');

    // Variable to store the currently selected chat
    let currentChat = '';

    /**
     * Fetches the list of available chats from the server and populates the chat selector dropdown.
     */
    async function loadChats() {
        try {
            const response = await fetch('/api/chats');
            if (!response.ok) {
                throw new Error('Failed to load chats');
            }
            const chats = await response.json();
            chatSelector.innerHTML = '';
            chats.forEach(chat => {
                const option = document.createElement('option');
                option.value = chat.name;
                option.textContent = chat.name;
                chatSelector.appendChild(option);
            });
            // If there are any chats, load the first one by default
            if (chats.length > 0) {
                currentChat = chats[0].name;
                loadMessages(currentChat);
            }
        } catch (error) {
            console.error(error);
            messagesDiv.innerHTML = '<p>Error loading chats.</p>';
        }
    }

    function createMessageElement(msg) {
        const container = document.createElement('div');
        container.style.marginBottom = '10px';
        
        const p = document.createElement('p');
        p.style.margin = '0';
        
        if (msg.role === 'user') {
            p.innerHTML = `<strong>${msg.role}:</strong> ${msg.content}`;
            container.appendChild(p);
        } else {
            // Assistant message
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.alignItems = 'center';
            header.style.gap = '10px';

            const roleTitle = document.createElement('strong');
            roleTitle.textContent = `${msg.role}:`;
            header.appendChild(roleTitle);

            // Heart icon
            const heart = document.createElement('span');
            heart.textContent = msg.liked ? '❤️' : '♡';
            heart.style.fontSize = '1.25em';
            heart.style.cursor = 'pointer';
            heart.style.userSelect = 'none';
            heart.onclick = async () => {
                try {
                    const response = await fetch(`/api/messages/${msg.id}/like`, { method: 'POST' });
                    if (response.ok) {
                        const data = await response.json();
                        heart.textContent = data.liked ? '❤️' : '♡';
                    }
                } catch (err) {
                    console.error('Error toggling like', err);
                }
            };
            header.appendChild(heart);
            container.appendChild(header);

            const contentDiv = document.createElement('div');
            const contentParts = get_split_message(msg.content);
            contentParts.forEach(c => contentDiv.appendChild(c));
            container.appendChild(contentDiv);
        }
        return container;
    }

    /**
     * Fetches the messages for a given chat and displays them in the messages div.
     * @param {string} chat - The name of the chat to load.
     */
    async function loadMessages(chat) {
        try {
            const response = await fetch(`/api/chats/${chat}`);
            if (!response.ok) {
                throw new Error('Failed to load messages');
            }
            const messages = await response.json();
            messagesDiv.innerHTML = '';
            messages.forEach(msg => {
                messagesDiv.appendChild(createMessageElement(msg));
            });
            // Scroll to the bottom of the messages div
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } catch (error) {
            console.error(error);
            messagesDiv.innerHTML = `<p>Error loading messages for ${chat}.</p>`;
        }
    }

    function get_split_message(message) {
        var messageDivs = [];
        const content_split = message.split("###");
        for (let ii = 0; ii < content_split.length; ii++) {
            if (content_split[ii] == "") {
                continue;
            }
            else if (ii > 1) {
                messageDivs.push(document.createElement("br"));
                messageDivs.push(document.createElement("br"));
            }
            messageDivs.push(document.createTextNode(content_split[ii]));
        }
        return messageDivs;
    }

    /**
     * Sends a new message to the server and displays the response.
     * @param {Event} e - The form submission event.
     */
    async function sendMessage(e) {
        e.preventDefault();
        const content = messageInput.value.trim();
        if (!content || !currentChat) {
            return;
        }

        const submitButton = messageForm.querySelector('button');
        const message = {
            role: 'user',
            content: "Tell a revenge story about " + content
        };

        // Disable input and button
        messageInput.disabled = true;
        submitButton.disabled = true;
        messageInput.value = '';

        // Add user message immediately
        messagesDiv.appendChild(createMessageElement({ role: 'user', content: message.content }));
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        // Add placeholder
        const placeholder = document.createElement('div');
        placeholder.textContent = 'Asking Grok...';
        placeholder.style.padding = '10px';
        placeholder.style.color = '#555';
        placeholder.style.fontStyle = 'italic';
        messagesDiv.appendChild(placeholder);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        try {
            // Send the new message to the server
            const response = await fetch(`/api/chats/${currentChat}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(message)
            });

            // Remove placeholder
            if (placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
            }

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            // Wait for the bot's response and add it to the UI
            const botMessage = await response.json();
            messagesDiv.appendChild(createMessageElement(botMessage));
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } catch (error) {
            console.error(error);
            if (placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
            }
            // Optionally, display an error message in the UI
        } finally {
            // Re-enable input and button
            messageInput.disabled = false;
            submitButton.disabled = false;
            messageInput.focus();
        }
    }

    // Event listener for when the user selects a different chat
    chatSelector.addEventListener('change', (e) => {
        currentChat = e.target.value;
        loadMessages(currentChat);
    });

    // Event listener for when the user submits the message form
    messageForm.addEventListener('submit', sendMessage);

    // Load the chats when the page is first loaded
    loadChats();
});
