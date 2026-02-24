// FutureMessage Chain Frontend Application
class FutureMessageApp {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.contract = null;
        this.apiBase = 'http://localhost:5000/api';
        this.isDarkMode = false;

        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.loadTheme();
        this.updateBlockchainTimestamp();

        // Update timestamp every 30 seconds
        setInterval(() => this.updateBlockchainTimestamp(), 30000);

        // Check if MetaMask is installed
        if (typeof window.ethereum !== 'undefined') {
            this.web3 = new Web3(window.ethereum);
        }
    }

    setupEventListeners() {
        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => this.toggleTheme());

        // Wallet connection
        document.getElementById('connect-wallet')?.addEventListener('click', () => this.connectWallet());

        // Navigation
        document.getElementById('get-started')?.addEventListener('click', () => this.showDashboard());
        document.getElementById('learn-more')?.addEventListener('click', () => this.showLearnMore());

    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        document.body.classList.toggle('dark', this.isDarkMode);
        localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');

        const icon = document.querySelector('#theme-toggle i');
        icon.className = this.isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            this.isDarkMode = true;
            document.body.classList.add('dark');
            document.querySelector('#theme-toggle i').className = 'fas fa-sun';
        }
    }

    async connectWallet() {
        try {
            if (!this.web3) {
                alert('Please install MetaMask to use this application!');
                return;
            }

            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            this.account = accounts[0];

            document.getElementById('connect-wallet').innerHTML = `
                <i class="fas fa-check-circle mr-2"></i>
                ${this.account.substring(0, 6)}...${this.account.substring(this.account.length - 4)}
            `;

            this.showDashboard();


        } catch (error) {
            console.error('Wallet connection failed:', error);
            alert('Failed to connect wallet. Please try again.');
        }
    }

    async updateBlockchainTimestamp() {
        try {
            const response = await fetch(`${this.apiBase}/blockchain/timestamp`);
            const data = await response.json();

            if (data.timestamp) {
                const date = new Date(data.timestamp * 1000);
                document.getElementById('blockchain-timestamp').textContent =
                    date.toLocaleString();
            }
        } catch (error) {
            console.error('Failed to fetch blockchain timestamp:', error);
        }
    }

    showDashboard() {
        if (!this.account) {
            alert('Please connect your wallet first!');
            return;
        }

        // Redirect to dashboard page
        window.location.href = '/dashboard';
    }


    async loadMessages() {
        try {
            const response = await fetch(`${this.apiBase}/messages?wallet_address=${this.account}`);
            const data = await response.json();

            this.renderMessages(data.messages);
        } catch (error) {
            console.error('Failed to load messages:', error);
        }
    }

    renderMessages(messages) {
        const container = document.querySelector('.messages-container') || this.createMessagesContainer();

        container.innerHTML = '<h2 class="text-2xl font-bold text-white mb-6">Your Messages</h2>';

        if (messages.length === 0) {
            container.innerHTML += `
                <div class="glassmorphism rounded-xl p-8 text-center">
                    <i class="fas fa-inbox text-4xl text-gray-400 mb-4"></i>
                    <p class="text-gray-300">No messages yet. Create your first time-locked message!</p>
                </div>
            `;
            return;
        }

        messages.forEach(message => {
            const messageCard = this.createMessageCard(message);
            container.appendChild(messageCard);
        });
    }

    createMessagesContainer() {
        const container = document.createElement('div');
        container.className = 'messages-container max-w-4xl mx-auto px-4 py-8';

        // Insert after hero section
        const heroSection = document.querySelector('section');
        heroSection.insertAdjacentElement('afterend', container);

        return container;
    }

    createMessageCard(message) {
        const unlockDate = new Date(message.unlock_time * 1000);
        const now = new Date();
        const canReveal = message.can_reveal;
        const isRevealed = message.is_revealed;

        const card = document.createElement('div');
        card.className = 'glassmorphism rounded-xl p-6 mb-4';

        card.innerHTML = `
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-full flex items-center justify-center ${
                        message.message_type === 'image' ? 'bg-blue-500' :
                        message.message_type === 'document' ? 'bg-green-500' : 'bg-purple-500'
                    }">
                        <i class="fas fa-${
                            message.message_type === 'image' ? 'image' :
                            message.message_type === 'document' ? 'file' : 'comment'
                        } text-white"></i>
                    </div>
                    <div>
                        <p class="text-white font-semibold">${message.message_type.toUpperCase()} MESSAGE</p>
                        <p class="text-gray-300 text-sm">From: ${message.sender.substring(0, 6)}...${message.sender.substring(message.sender.length - 4)}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-white font-semibold" id="countdown-${message.id}">--</p>
                    <p class="text-gray-300 text-sm">${canReveal ? 'Ready to reveal' : 'Locked'}</p>
                </div>
            </div>

            <div class="flex justify-between items-center">
                <div class="text-sm text-gray-300">
                    <p>Unlock: ${unlockDate.toLocaleString()}</p>
                    <p>Created: ${new Date(message.created_time * 1000).toLocaleString()}</p>
                </div>
                <div class="flex space-x-2">
                    ${isRevealed ? `
                        <button onclick="app.downloadMessage('${message.ipfs_hash}')"
                                class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition duration-300">
                            <i class="fas fa-download mr-2"></i>Download
                        </button>
                    ` : ''}
                    <button onclick="app.deleteMessage(${message.id})"
                            class="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition duration-300">
                        <i class="fas fa-trash mr-2"></i>Delete
                    </button>
                </div>
            </div>
        `;

        // Start countdown timer
        this.startCountdown(message.id, message.unlock_time);

        return card;
    }

    startCountdown(messageId, unlockTime) {
        const updateCountdown = () => {
            const now = Math.floor(Date.now() / 1000);
            const remaining = unlockTime - now;

            if (remaining <= 0) {
                document.getElementById(`countdown-${messageId}`).textContent = 'Unlocked!';
                // Auto-reveal the message when time is up
                if (!message.is_revealed) {
                    this.autoRevealMessage(messageId);
                }
                // Clear interval when countdown is complete
                if (this.countdownIntervals && this.countdownIntervals[messageId]) {
                    clearInterval(this.countdownIntervals[messageId]);
                    delete this.countdownIntervals[messageId];
                }
                return;
            }

            const days = Math.floor(remaining / 86400);
            const hours = Math.floor((remaining % 86400) / 3600);
            const minutes = Math.floor((remaining % 3600) / 60);
            const seconds = remaining % 60;

            document.getElementById(`countdown-${messageId}`).textContent =
                `${days}d ${hours}h ${minutes}m ${seconds}s`;
        };

        updateCountdown();
        const interval = setInterval(updateCountdown, 1000);

        // Store interval ID for cleanup
        if (!this.countdownIntervals) {
            this.countdownIntervals = {};
        }
        this.countdownIntervals[messageId] = interval;
    }

    // Cleanup method to clear all countdown intervals
    clearAllCountdowns() {
        if (this.countdownIntervals) {
            Object.values(this.countdownIntervals).forEach(interval => {
                clearInterval(interval);
            });
            this.countdownIntervals = {};
        }
    }

    async revealMessage(messageId) {
        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/reveal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_address: this.account })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Message revealed: ${data.content}`);
                this.loadMessages(); // Refresh messages
            } else {
                alert('Failed to reveal message: ' + data.error);
            }
        } catch (error) {
            console.error('Reveal failed:', error);
            alert('Failed to reveal message');
        }
    }

    async autoRevealMessage(messageId) {
        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/reveal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_address: this.account })
            });

            const data = await response.json();

            if (data.success) {
                // Auto-download for binary content (images/documents)
                if (data.is_binary && data.content) {
                    try {
                        const binaryData = atob(data.content);
                        const bytes = new Uint8Array(binaryData.length);
                        for (let i = 0; i < binaryData.length; i++) {
                            bytes[i] = binaryData.charCodeAt(i);
                        }
                        const blob = new Blob([bytes], { type: 'application/octet-stream' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        let extension = '';
                        if (data.message_type === 'image') extension = 'png';
                        else if (data.message_type === 'document') extension = 'pdf';
                        a.download = `revealed_message_${Date.now()}.${extension}`;
                        document.body.appendChild(a);
                        a.click();
                        setTimeout(() => {
                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);
                        }, 1000);
                    } catch (e) {
                        console.error('Auto-download failed:', e);
                    }
                }
                // Show notification
                this.showNotification(`Message ${messageId} has been automatically revealed!`, 'success');
                this.loadMessages(); // Refresh messages
            } else {
                console.error('Auto-reveal failed:', data.error);
            }
        } catch (error) {
            console.error('Auto-reveal failed:', error);
        }
    }

    async deleteMessage(messageId) {
        if (!confirm('Are you sure you want to delete this message?')) return;

        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/delete`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_address: this.account })
            });

            const data = await response.json();

            if (data.success) {
                this.loadMessages(); // Refresh messages
            } else {
                alert('Failed to delete message: ' + data.error);
            }
        } catch (error) {
            console.error('Delete failed:', error);
            alert('Failed to delete message');
        }
    }

    async downloadMessage(ipfsHash) {
        try {
            const response = await fetch(`${this.apiBase}/download/${ipfsHash}?wallet_address=${this.account}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();

            // Determine file extension based on content type
            let extension = '';
            const contentType = response.headers.get('content-type');
            if (contentType) {
                if (contentType.includes('image/png')) extension = '.png';
                else if (contentType.includes('image/jpeg') || contentType.includes('image/jpg')) extension = '.jpg';
                else if (contentType.includes('application/pdf')) extension = '.pdf';
                else if (contentType.includes('text/plain')) extension = '.txt';
                else if (contentType.includes('application/zip')) extension = '.zip';
            }

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `revealed_message_${ipfsHash.substring(0, 8)}${extension}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success message
            this.showNotification('File downloaded successfully!', 'success');
        } catch (error) {
            console.error('Download failed:', error);
            this.showNotification('Failed to download message', 'error');
        }
    }

    // Add notification method
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    showLearnMore() {
        // Scroll to features section or show modal
        document.querySelector('.grid.md\\:grid-cols-3')?.scrollIntoView({ behavior: 'smooth' });
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new FutureMessageApp();
});
