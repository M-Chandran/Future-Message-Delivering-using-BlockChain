 // Dashboard JavaScript - FutureMessage Chain
class DashboardApp {
    constructor() {
        this.apiBase = '/api';
        this.countdownIntervals = {};
        this.init();
    }

    init() {
        this.startCountdowns();
        this.updateStats();
    }

    // Start countdown timers for all messages
    startCountdowns() {
        const messageCards = document.querySelectorAll('.message-card');
        
        messageCards.forEach(card => {
            const messageId = card.dataset.messageId;
            const unlockTime = card.dataset.unlockTime;
            const status = card.dataset.status;

            if (status !== 'revealed') {
                this.startCountdown(messageId, unlockTime);
            }
        });
    }

    // Start individual countdown
    startCountdown(messageId, unlockTime) {
        const updateCountdown = () => {
            const now = new Date().getTime();
            const unlockDate = new Date(unlockTime).getTime();
            const remaining = unlockDate - now;

            const timeElement = document.getElementById(`time-${messageId}`);
            const countdownElement = document.getElementById(`countdown-${messageId}`);
            const revealBtn = document.getElementById(`reveal-btn-${messageId}`);

            if (remaining <= 0) {
                // Time is up - unlock the message
                timeElement.textContent = 'UNLOCKED';
                countdownElement.classList.add('unlocked');
                countdownElement.querySelector('i').className = 'fas fa-unlock';
                countdownElement.querySelector('.label').textContent = 'Ready to reveal!';
                
                // Enable reveal button
                revealBtn.disabled = false;
                revealBtn.innerHTML = '<i class="fas fa-eye"></i> Reveal Message';
                
                // Update card styling
                const card = document.querySelector(`[data-message-id="${messageId}"]`);
                if (card) {
                    card.classList.add('unlocked');
                    card.dataset.status = 'unlocked';
                }

                // Auto-reveal if needed
                this.autoRevealMessage(messageId);

                // Clear interval
                if (this.countdownIntervals[messageId]) {
                    clearInterval(this.countdownIntervals[messageId]);
                    delete this.countdownIntervals[messageId];
                }

                // Update status on server
                this.updateMessageStatus(messageId, 'unlocked');
            } else {
                // Calculate time components
                const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
                const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((remaining % (1000 * 60)) / 1000);

                // Update display
                timeElement.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
            }
        };

        // Update immediately and then every second
        updateCountdown();
        this.countdownIntervals[messageId] = setInterval(updateCountdown, 1000);
    }

    // Update message status on server
    async updateMessageStatus(messageId, status) {
        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status })
            });

            if (!response.ok) {
                console.error('Failed to update message status');
            }
        } catch (error) {
            console.error('Error updating message status:', error);
        }
    }


    // Auto-reveal message when unlocked
    async autoRevealMessage(messageId) {
        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/reveal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });


            if (response.ok) {
                const data = await response.json();
                this.showNotification('Message auto-revealed!', 'success');
                
                // Update UI to show revealed content - FIX: use correct ID
                const contentElement = document.getElementById(`revealed-content-${messageId}`);
                if (contentElement && data.content) {
                    // Show the container
                    contentElement.style.display = 'block';
                    
                    // Handle different message types
                    if (data.message_type === 'text' || data.is_binary === false) {
                        // Text message - display as formatted text
                        contentElement.innerHTML = `<h4><i class="fas fa-envelope-open"></i> Your Message:</h4><div class="revealed-text">${this.escapeHtml(data.content)}</div>`;
                    } else if (data.message_type === 'image') {
                        // Image - display as base64 image
                        contentElement.innerHTML = `<h4><i class="fas fa-image"></i> Your Image:</h4><img src="data:image/png;base64,${data.content}" alt="Revealed Image" class="revealed-image">`;
                    } else if (data.message_type === 'document') {
                        contentElement.innerHTML = `<h4><i class="fas fa-file-alt"></i> Your Document:</h4><div class="revealed-text">Your document is ready. Download started automatically.</div>`;
                        this.triggerDownload(messageId);
                    } else {
                        // Default - just display content
                        contentElement.innerHTML = `<h4><i class="fas fa-file-alt"></i> Content:</h4><div class="revealed-text">${this.escapeHtml(data.content)}</div>`;
                    }
                    contentElement.classList.add('revealed');
                }
            }
        } catch (error) {
            console.error('Auto-reveal error:', error);
        }
    }

    async revealMessage(messageId, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        const revealBtn = document.getElementById(`reveal-btn-${messageId}`);
        const originalText = revealBtn.innerHTML;
        
        try {
            revealBtn.disabled = true;
            revealBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Revealing...';

            const response = await fetch(`${this.apiBase}/messages/${messageId}/reveal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });


            const data = await response.json();

            if (response.ok) {
                // Update UI - FIX: use correct ID
                const contentElement = document.getElementById(`revealed-content-${messageId}`);
                const card = document.querySelector(`[data-message-id="${messageId}"]`);
                
                if (contentElement && data.content) {
                    // Show the container
                    contentElement.style.display = 'block';
                    
                    // Handle different message types
                    if (data.message_type === 'text' || data.is_binary === false) {
                        // Text message - display as formatted text
                        contentElement.innerHTML = `<h4><i class="fas fa-envelope-open"></i> Your Message:</h4><div class="revealed-text">${this.escapeHtml(data.content)}</div>`;
                    } else if (data.message_type === 'image') {
                        // Image - display as base64 image
                        contentElement.innerHTML = `<h4><i class="fas fa-image"></i> Your Image:</h4><img src="data:image/png;base64,${data.content}" alt="Revealed Image" class="revealed-image">`;
                    } else if (data.message_type === 'document') {
                        contentElement.innerHTML = `<h4><i class="fas fa-file-alt"></i> Your Document:</h4><div class="revealed-text">Your document is ready. Download started automatically.</div>`;
                        this.triggerDownload(messageId);
                    } else {
                        // Default - just display content
                        contentElement.innerHTML = `<h4><i class="fas fa-file-alt"></i> Content:</h4><div class="revealed-text">${this.escapeHtml(data.content)}</div>`;
                    }
                    contentElement.classList.add('revealed');
                }

                // Update card status
                if (card) {
                    card.dataset.status = 'revealed';
                    card.classList.add('revealed');
                }

                // Update button
                revealBtn.innerHTML = '<i class="fas fa-check"></i> Revealed';
                revealBtn.classList.add('revealed');

                this.showNotification('Message revealed successfully!', 'success');
                this.updateStats();
            } else {
                throw new Error(data.error || 'Failed to reveal message');
            }
        } catch (error) {
            console.error('Reveal error:', error);
            this.showNotification('Failed to reveal message: ' + error.message, 'error');
            
            // Reset button
            revealBtn.disabled = false;
            revealBtn.innerHTML = originalText;
        }
    }

    // Delete message - FIXED: Added event parameter
    async deleteMessage(messageId, event) {
        // FIXED: Prevent default and stop propagation
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!confirm('Are you sure you want to delete this message?')) {
            return;
        }


        try {
            const response = await fetch(`${this.apiBase}/messages/${messageId}/delete`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });



            if (response.ok) {
                // Remove card from UI
                const card = document.querySelector(`[data-message-id="${messageId}"]`);
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(-20px)';
                    setTimeout(() => {
                        card.remove();
                        this.updateStats();
                        
                        // Check if no messages left
                        const remainingCards = document.querySelectorAll('.message-card');
                        if (remainingCards.length === 0) {
                            window.location.reload();
                        }
                    }, 300);
                }
            } else {
                const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(errorData.error || `Failed to delete message: ${response.status}`);
            }


        } catch (error) {
            console.error('Delete error:', error);
            this.showNotification('Failed to delete message: ' + error.message, 'error');
        }
    }

    // Update statistics
    updateStats() {
        const totalMessages = document.querySelectorAll('.message-card').length;
        const unlockedMessages = document.querySelectorAll('.message-card[data-status="unlocked"]').length;
        const lockedMessages = document.querySelectorAll('.message-card[data-status="locked"]').length;
        const revealedMessages = document.querySelectorAll('.message-card[data-status="revealed"]').length;

        // Update stat cards if they exist
        const totalElement = document.getElementById('total-messages');
        const unlockedElement = document.getElementById('unlocked-count');
        const lockedElement = document.getElementById('locked-count');
        const revealedElement = document.getElementById('revealed-count');

        if (totalElement) totalElement.textContent = totalMessages;
        if (unlockedElement) unlockedElement.textContent = unlockedMessages;
        if (lockedElement) lockedElement.textContent = lockedMessages;
        if (revealedElement) revealedElement.textContent = revealedMessages;
    }

    // Show notification
    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelector('.notification');
        if (existing) {
            existing.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }
        }, 3000);
    }

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Trigger file download without navigating away from dashboard
    triggerDownload(messageId) {
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = `/api/download/${messageId}`;
        document.body.appendChild(iframe);
        setTimeout(() => {
            if (iframe.parentNode) {
                iframe.parentNode.removeChild(iframe);
            }
        }, 5000);
    }

    // Cleanup on page unload
    cleanup() {
        Object.values(this.countdownIntervals).forEach(interval => {
            clearInterval(interval);
        });
        this.countdownIntervals = {};
    }
}

// Initialize dashboard
const dashboard = new DashboardApp();

// Global wrapper functions for HTML onclick handlers
function revealMessage(messageId, event) {
    return dashboard.revealMessage(messageId, event);
}

function deleteMessage(messageId, event) {
    return dashboard.deleteMessage(messageId, event);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    dashboard.cleanup();
});

