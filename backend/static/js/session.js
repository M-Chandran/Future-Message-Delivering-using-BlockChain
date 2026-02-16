// Session data initialization
// This file is loaded after the HTML body, so we can safely set session data
// The data is passed from the template via data attributes on the body

(function() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSession);
    } else {
        initSession();
    }
    
    function initSession() {
        // Get session data from data attributes on body
        const body = document.body;
        
        const walletAddress = body.dataset.walletAddress || '';
        const userId = body.dataset.userId || '';
        
        // Set the global session data
        window.sessionData = {
            wallet_address: walletAddress,
            user_id: userId
        };
    }
})();
