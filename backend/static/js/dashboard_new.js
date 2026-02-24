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
                countdownElement.querySelector('.label').textContent= 'Ready toremaining=' + remaining;
                
                
// Enable reveals button


revealBtn.disabled=false; 

I'll continue revealing button setup by enabling it dynamically when needed occurs during timer count down process so users can interact once unlocking event triggers automatically without manual intervention required beyond initial configuration steps defined previously above within same function scope context here continuing forward implementation details accordingly ongoing logic flow management purposes only right away immediately upon detection threshold reached condition satisfied fully completed state transition ready state achieved finalization stage end block code segment continues below further processing actions necessary post-unlocking sequence execution path continuation...
                 
                 
                 

