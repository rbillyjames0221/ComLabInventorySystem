// Alerts Notification System
(function() {
    'use strict';

    let alertsCount = 0;
    let alertsList = [];
    let alertsPanelOpen = false;
    let refreshInterval = null;

    // Initialize alerts system
    function initAlerts() {
        const alertsBtn = document.getElementById('alertsBtn');
        const alertsBtnMobile = document.getElementById('alertsBtnMobile');
        const alertsPanel = document.getElementById('alertsPanel');
        const alertsBadge = document.getElementById('alertsBadge');
        const alertsBadgeMobile = document.getElementById('alertsBadgeMobile');
        const alertsList = document.getElementById('alertsList');

        // Use mobile or desktop button
        const activeAlertsBtn = alertsBtnMobile || alertsBtn;
        const activeAlertsPanel = alertsPanel;
        const activeAlertsBadge = alertsBadgeMobile || alertsBadge;

        if (!activeAlertsBtn) return;

        // Load initial alerts count
        loadAlertsCount();
        loadAlertsList();

        // Toggle alerts panel (both desktop and mobile)
        if (alertsBtn) {
            alertsBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleAlertsPanel();
            });
        }
        
        if (alertsBtnMobile) {
            alertsBtnMobile.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleAlertsPanel();
            });
        }

        // Close panel when clicking outside
        document.addEventListener('click', function(e) {
            if (alertsPanelOpen && alertsPanel) {
                const clickedAlertsBtn = alertsBtn && alertsBtn.contains(e.target);
                const clickedAlertsBtnMobile = alertsBtnMobile && alertsBtnMobile.contains(e.target);
                const clickedInsidePanel = alertsPanel.contains(e.target);
                
                if (!clickedInsidePanel && !clickedAlertsBtn && !clickedAlertsBtnMobile) {
                    closeAlertsPanel();
                }
            }
        });

        // Close panel on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && alertsPanelOpen) {
                closeAlertsPanel();
            }
        });

        // Auto-refresh alerts every 30 seconds
        refreshInterval = setInterval(function() {
            loadAlertsCount();
            if (alertsPanelOpen) {
                loadAlertsList();
            }
        }, 30000);

        // Listen to Server-Sent Events for real-time alerts
        if (typeof EventSource !== 'undefined') {
            const eventSource = new EventSource('/alerts/stream');
            
            eventSource.onmessage = function(e) {
                const [comlab_id, serial, alert_type] = e.data.split('|');
                handleNewAlert(comlab_id, serial, alert_type);
            };

            eventSource.onerror = function(e) {
                console.error('EventSource failed:', e);
                // EventSource will automatically reconnect
            };
        }
    }

    function loadAlertsCount() {
        fetch('/api/alerts/count')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alertsCount = data.count || 0;
                    updateAlertsBadge();
                }
            })
            .catch(error => {
                console.error('Error loading alerts count:', error);
            });
    }

    function loadAlertsList() {
        const alertsListEl = document.getElementById('alertsList');
        const alertsListMobile = document.getElementById('alertsListMobile');
        
        if (!alertsListEl && !alertsListMobile) return;

        const loadingHtml = '<div class="alerts-loading">Loading alerts...</div>';
        if (alertsListEl) alertsListEl.innerHTML = loadingHtml;
        if (alertsListMobile) alertsListMobile.innerHTML = loadingHtml;

        fetch('/api/alerts/list')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alertsList = data.alerts || [];
                    renderAlertsList();
                } else {
                    const errorHtml = '<div class="alerts-empty">Error loading alerts</div>';
                    if (alertsListEl) alertsListEl.innerHTML = errorHtml;
                    if (alertsListMobile) alertsListMobile.innerHTML = errorHtml;
                }
            })
            .catch(error => {
                console.error('Error loading alerts list:', error);
                const errorHtml = '<div class="alerts-empty">Error loading alerts</div>';
                if (alertsListEl) alertsListEl.innerHTML = errorHtml;
                if (alertsListMobile) alertsListMobile.innerHTML = errorHtml;
            });
    }

    function renderAlertsList() {
        const alertsListEl = document.getElementById('alertsList');
        const alertsListMobile = document.getElementById('alertsListMobile');
        
        if (!alertsListEl && !alertsListMobile) return;

        let html = '';
        if (alertsList.length === 0) {
            html = '<div class="alerts-empty">No active alerts</div>';
            if (alertsListEl) alertsListEl.innerHTML = html;
            if (alertsListMobile) alertsListMobile.innerHTML = html;
            updateViewAllLink();
            return;
        }

        alertsList.forEach(alert => {
            const alertType = alert.alert_type || 'unknown';
            const iconClass = alertType === 'faulty' ? 'faulty' : 
                             alertType === 'missing' ? 'missing' : 
                             alertType === 'replaced' ? 'replaced' : 'unknown';
            const icon = alertType === 'faulty' ? '⚠️' : 
                        alertType === 'missing' ? '🔍' : 
                        alertType === 'replaced' ? '🔄' : 'ℹ️';
            const title = `${alert.device_name || 'Device'} (${alert.serial_number})`;
            const desc = `${alertType.charAt(0).toUpperCase() + alertType.slice(1)} - ${alert.lab_name || 'Lab ' + alert.comlab_id}`;
            const time = formatTime(alert.timestamp);

            html += `
                <div class="alerts-item" onclick="viewAlertDetails(${alert.comlab_id}, '${alert.alert_type}')">
                    <div class="alerts-item-icon ${iconClass}">${icon}</div>
                    <div class="alerts-item-content">
                        <div class="alerts-item-title">${escapeHtml(title)}</div>
                        <div class="alerts-item-desc">${escapeHtml(desc)}</div>
                        <div class="alerts-item-time">${time}</div>
                    </div>
                </div>
            `;
        });

        if (alertsListEl) alertsListEl.innerHTML = html;
        if (alertsListMobile) alertsListMobile.innerHTML = html;
        updateViewAllLink();
    }

    function updateViewAllLink() {
        const viewAllLink = document.getElementById('viewAllAlertsLink');
        const viewAllLinkMobile = document.getElementById('viewAllAlertsLinkMobile');
        
        const updateLink = (link) => {
            if (link) {
                if (alertsList.length > 0) {
                    // Find the first lab with alerts
                    const firstLab = alertsList[0];
                    if (firstLab && firstLab.comlab_id) {
                        link.href = `/comlab/${firstLab.comlab_id}/inventory/view_alerts`;
                    } else {
                        link.href = '/admin';
                    }
                } else {
                    link.href = '/admin';
                }
            }
        };
        
        updateLink(viewAllLink);
        updateLink(viewAllLinkMobile);
    }
    
    // Expose loadAlertsList globally for topbar-menu.js
    window.loadAlertsList = loadAlertsList;

    function updateAlertsBadge() {
        const alertsBadge = document.getElementById('alertsBadge');
        const alertsBadgeMobile = document.getElementById('alertsBadgeMobile');
        
        const updateBadge = (badge) => {
            if (!badge) return;
            if (alertsCount > 0) {
                badge.textContent = alertsCount > 99 ? '99+' : alertsCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        };
        
        updateBadge(alertsBadge);
        updateBadge(alertsBadgeMobile);
    }

    function toggleAlertsPanel() {
        const alertsPanel = document.getElementById('alertsPanel');
        if (!alertsPanel) return;

        if (alertsPanelOpen) {
            closeAlertsPanel();
        } else {
            openAlertsPanel();
        }
    }

    function openAlertsPanel() {
        const alertsPanel = document.getElementById('alertsPanel');
        if (!alertsPanel) return;

        alertsPanelOpen = true;
        alertsPanel.classList.add('active');
        loadAlertsList();
    }

    function closeAlertsPanel() {
        const alertsPanel = document.getElementById('alertsPanel');
        if (!alertsPanel) return;

        alertsPanelOpen = false;
        alertsPanel.classList.remove('active');
    }

    function handleNewAlert(comlab_id, serial, alert_type) {
        // Refresh alerts count and list
        loadAlertsCount();
        if (alertsPanelOpen) {
            loadAlertsList();
        }

        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            const title = 'New Device Alert';
            const body = `Device ${serial} is ${alert_type.toUpperCase()}`;
            new Notification(title, { body: body, icon: '/static/default-avatar.jpg' });
        }
    }

    function formatTime(timestamp) {
        if (!timestamp) return 'Just now';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Request notification permission on page load
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAlerts);
    } else {
        initAlerts();
    }

    // Expose functions globally
    window.viewAlertDetails = function(comlab_id, alert_type) {
        window.location.href = `/comlab/${comlab_id}/inventory/view_alerts${alert_type ? '?alert_type=' + alert_type : ''}`;
    };

    window.closeAlertsPanel = closeAlertsPanel;
    window.toggleAlertsPanel = toggleAlertsPanel;

    // Update view all alerts link
    document.addEventListener('DOMContentLoaded', function() {
        const viewAllLink = document.getElementById('viewAllAlertsLink');
        if (viewAllLink && alertsList.length > 0) {
            // Find the first lab with alerts
            const firstLab = alertsList[0];
            if (firstLab && firstLab.comlab_id) {
                viewAllLink.href = `/comlab/${firstLab.comlab_id}/inventory/view_alerts`;
            } else {
                viewAllLink.href = '/admin';
            }
        }
    });

})();

