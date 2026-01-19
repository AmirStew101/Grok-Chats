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
                option.value = chat;
                option.textContent = chat;
                chatSelector.appendChild(option);
            });
            // If there are any chats, load the first one by default
            if (chats.length > 0) {
                currentChat = chats[0];
                loadMessages(currentChat);
            }
        } catch (error) {
            console.error(error);
            messagesDiv.innerHTML = '<p>Error loading chats.</p>';
        }
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
                const p = document.createElement('p');
                p.textContent = `${msg.role}: ${msg.content}`;
                messagesDiv.appendChild(p);
            });
            // Scroll to the bottom of the messages div
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } catch (error) {
            console.error(error);
            messagesDiv.innerHTML = `<p>Error loading messages for ${chat}.</p>`;
        }
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

        const message = {
            role: 'user',
            content: "Tell a revenge story about " + content
        };

        try {
            // Send the new message to the server
            const response = await fetch(`/api/chats/${currentChat}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(message)
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            messageInput.value = '';
            // Optimistically add the user's message to the UI
            const p = document.createElement('p');
            p.textContent = `${message.role}: ${message.content}`;
            messagesDiv.appendChild(p);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            // Wait for the bot's response and add it to the UI
            const botMessage = await response.json();
            const pBot = document.createElement('p');
            pBot.textContent = `${botMessage.role}: ${botMessage.content}`;
            messagesDiv.appendChild(pBot);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;


        } catch (error) {
            console.error(error);
            // Optionally, display an error message in the UI
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
