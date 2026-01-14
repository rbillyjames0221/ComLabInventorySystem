// Topbar Menu and 3-Dots Dropdown Handler

(function() {
    'use strict';

    function initTopbarMenu() {
        const moreMenuBtn = document.getElementById('moreMenuBtn');
        const moreMenuDropdown = document.getElementById('moreMenuDropdown');
        const alertsBtnMenu = document.getElementById('alertsBtnMenu');
        const alertsPanelMobile = document.getElementById('alertsPanelMobile');

        if (!moreMenuBtn || !moreMenuDropdown) return;

        // Toggle more menu dropdown
        moreMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleMoreMenu();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (moreMenuDropdown && moreMenuDropdown.classList.contains('active')) {
                if (!moreMenuDropdown.contains(e.target) && !moreMenuBtn.contains(e.target)) {
                    closeMoreMenu();
                }
            }
        });

        // Handle alerts button in dropdown menu
        if (alertsBtnMenu) {
            alertsBtnMenu.addEventListener('click', function(e) {
                e.stopPropagation();
                if (alertsPanelMobile) {
                    openAlertsPanelMobile();
                    closeMoreMenu();
                } else {
                    // Fallback: try desktop alerts panel
                    const alertsBtn = document.getElementById('alertsBtn');
                    if (alertsBtn) {
                        alertsBtn.click();
                    }
                }
            });
        }

        // Close on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                if (moreMenuDropdown && moreMenuDropdown.classList.contains('active')) {
                    closeMoreMenu();
                }
                if (alertsPanelMobile && alertsPanelMobile.classList.contains('active')) {
                    closeAlertsPanelMobile();
                }
            }
        });

        // Sync alerts badge between desktop and mobile menu
        syncAlertsBadge();
    }

    function toggleMoreMenu() {
        const moreMenuBtn = document.getElementById('moreMenuBtn');
        const moreMenuDropdown = document.getElementById('moreMenuDropdown');
        
        if (!moreMenuBtn || !moreMenuDropdown) return;

        const isActive = moreMenuDropdown.classList.contains('active');
        
        if (isActive) {
            closeMoreMenu();
        } else {
            openMoreMenu();
        }
    }

    function openMoreMenu() {
        const moreMenuBtn = document.getElementById('moreMenuBtn');
        const moreMenuDropdown = document.getElementById('moreMenuDropdown');
        
        if (moreMenuBtn && moreMenuDropdown) {
            moreMenuBtn.classList.add('active');
            moreMenuDropdown.classList.add('active');
        }
    }

    function closeMoreMenu() {
        const moreMenuBtn = document.getElementById('moreMenuBtn');
        const moreMenuDropdown = document.getElementById('moreMenuDropdown');
        
        if (moreMenuBtn && moreMenuDropdown) {
            moreMenuBtn.classList.remove('active');
            moreMenuDropdown.classList.remove('active');
        }
    }

    function openAlertsPanelMobile() {
        const alertsPanelMobile = document.getElementById('alertsPanelMobile');
        if (alertsPanelMobile) {
            alertsPanelMobile.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // Load alerts if not already loaded
            const alertsListMobile = document.getElementById('alertsListMobile');
            if (alertsListMobile && alertsListMobile.innerHTML.includes('Loading')) {
                // Trigger alerts load if alerts.js is available
                if (typeof window.loadAlertsList === 'function') {
                    window.loadAlertsList();
                } else if (window.alertsSystem && window.alertsSystem.loadAlertsList) {
                    window.alertsSystem.loadAlertsList();
                }
            }
        }
    }

    function closeAlertsPanelMobile() {
        const alertsPanelMobile = document.getElementById('alertsPanelMobile');
        if (alertsPanelMobile) {
            alertsPanelMobile.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    function syncAlertsBadge() {
        // Sync badge between desktop and mobile menu
        const alertsBadge = document.getElementById('alertsBadge');
        const alertsBadgeMenu = document.getElementById('alertsBadgeMenu');
        
        if (alertsBadge && alertsBadgeMenu) {
            // Watch for changes to desktop badge
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        const display = alertsBadge.style.display;
                        const text = alertsBadge.textContent;
                        
                        if (display === 'none') {
                            alertsBadgeMenu.style.display = 'none';
                        } else {
                            alertsBadgeMenu.style.display = 'inline-block';
                            alertsBadgeMenu.textContent = text;
                        }
                    }
                });
            });
            
            observer.observe(alertsBadge, {
                attributes: true,
                attributeFilter: ['style']
            });
            
            // Also watch text content changes
            const textObserver = new MutationObserver(function() {
                alertsBadgeMenu.textContent = alertsBadge.textContent;
            });
            
            textObserver.observe(alertsBadge, {
                childList: true,
                characterData: true
            });
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTopbarMenu);
    } else {
        initTopbarMenu();
    }

    // Expose functions globally
    window.closeAlertsPanelMobile = closeAlertsPanelMobile;
    window.openAlertsPanelMobile = openAlertsPanelMobile;
    window.closeMoreMenu = closeMoreMenu;
    window.openMoreMenu = openMoreMenu;

})();

