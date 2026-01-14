// Sidebar Navigation JavaScript

(function() {
    'use strict';

    // Initialize sidebar on DOM load
    document.addEventListener('DOMContentLoaded', function() {
        initSidebar();
    });

    function initSidebar() {
        const sidebar = document.getElementById('sidebar');
        const menuToggleBtn = document.getElementById('menuToggleBtn');
        const menuToggleMobileBtn = document.getElementById('menuToggleMobileBtn');
        const sidebarMobileToggle = document.getElementById('sidebarMobileToggle');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        const mainContent = document.querySelector('.main-content-wrapper');

        if (!sidebar) return;

        // Load saved sidebar state
        const savedState = localStorage.getItem('sidebarCollapsed');
        const isMobile = window.innerWidth <= 768;

        // Set initial state
        if (!isMobile && savedState === 'true') {
            sidebar.classList.add('collapsed');
        }

        // Desktop menu toggle button
        if (menuToggleBtn) {
            menuToggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (!isMobile) {
                    toggleSidebar();
                }
            });
        }

        // Mobile menu toggle button (opens sidebar from topbar)
        if (menuToggleMobileBtn) {
            menuToggleMobileBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (isMobile) {
                    openMobileSidebar();
                }
            });
        }

        // Mobile sidebar close button (inside sidebar)
        if (sidebarMobileToggle) {
            sidebarMobileToggle.addEventListener('click', function(e) {
                e.stopPropagation();
                if (isMobile) {
                    closeMobileSidebar();
                }
            });
        }

        // Close sidebar when clicking overlay
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', function() {
                closeMobileSidebar();
            });
        }

        // Close mobile sidebar when clicking outside
        document.addEventListener('click', function(e) {
            const isMobile = window.innerWidth <= 768;
            if (isMobile && sidebar.classList.contains('mobile-open')) {
                const menuToggleMobileBtn = document.getElementById('menuToggleMobileBtn');
                const sidebarMobileToggle = document.getElementById('sidebarMobileToggle');
                // Don't close if clicking on toggle buttons or inside sidebar
                if (!sidebar.contains(e.target) && 
                    (!menuToggleMobileBtn || !menuToggleMobileBtn.contains(e.target)) &&
                    (!sidebarMobileToggle || !sidebarMobileToggle.contains(e.target))) {
                    closeMobileSidebar();
                }
            }
        });

        // Handle window resize
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                handleResize();
            }, 250);
        });

        // Auto-expand submenu if current page is in it
        expandActiveSubmenu();

        // Swipe gesture support for mobile
        if (isMobile) {
            initSwipeGestures();
        }
    }

    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const isCollapsed = sidebar.classList.contains('collapsed');
        
        if (isCollapsed) {
            sidebar.classList.remove('collapsed');
            localStorage.setItem('sidebarCollapsed', 'false');
        } else {
            sidebar.classList.add('collapsed');
            localStorage.setItem('sidebarCollapsed', 'true');
        }
    }

    function openMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        
        if (!sidebar) return;

        sidebar.classList.add('mobile-open');
        if (sidebarOverlay) {
            sidebarOverlay.classList.add('active');
        }
        document.body.style.overflow = 'hidden'; // Prevent background scroll
    }

    function closeMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        
        if (!sidebar) return;

        sidebar.classList.remove('mobile-open');
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('active');
        }
        document.body.style.overflow = ''; // Restore scroll
    }

    function handleResize() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const isMobile = window.innerWidth <= 768;

        if (isMobile) {
            // On mobile, always close sidebar overlay
            closeMobileSidebar();
            sidebar.classList.remove('collapsed'); // Remove collapsed class on mobile
        } else {
            // On desktop, restore saved state
            const savedState = localStorage.getItem('sidebarCollapsed');
            if (savedState === 'true') {
                sidebar.classList.add('collapsed');
            } else {
                sidebar.classList.remove('collapsed');
            }
            // Close mobile overlay if open
            closeMobileSidebar();
        }
    }

    function expandActiveSubmenu() {
        const activeLink = document.querySelector('.menu-link.active, .submenu-link.active');
        if (!activeLink) return;

        // Find parent submenu
        const submenu = activeLink.closest('.submenu');
        if (submenu) {
            const menuItem = submenu.closest('.menu-item');
            if (menuItem) {
                menuItem.classList.add('open');
                const arrow = menuItem.querySelector('.menu-arrow');
                if (arrow) {
                    arrow.style.transform = 'rotate(180deg)';
                }
            }
        }
    }

    function initSwipeGestures() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        let touchStartX = 0;
        let touchEndX = 0;

        sidebar.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        sidebar.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });

        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;

            // Swipe left to close
            if (diff > swipeThreshold && sidebar.classList.contains('mobile-open')) {
                closeMobileSidebar();
            }
        }

        // Swipe from left edge to open
        let edgeTouchStart = null;
        document.addEventListener('touchstart', function(e) {
            if (e.touches[0].clientX < 20) { // Left edge
                edgeTouchStart = e.touches[0].screenX;
            }
        }, { passive: true });

        document.addEventListener('touchend', function(e) {
            if (edgeTouchStart !== null && !sidebar.classList.contains('mobile-open')) {
                const touchEnd = e.changedTouches[0].screenX;
                const diff = touchEnd - edgeTouchStart;
                
                if (diff > 50) { // Swipe right from edge
                    openMobileSidebar();
                }
            }
            edgeTouchStart = null;
        }, { passive: true });
    }

    // Global function for submenu toggle (called from HTML)
    window.toggleSubmenu = function(element) {
        const menuItem = element.closest('.menu-item');
        if (!menuItem) return;

        const submenu = menuItem.querySelector('.submenu');
        if (!submenu) return;

        const isOpen = menuItem.classList.contains('open');
        
        // Close all other submenus at same level
        const parent = menuItem.parentElement;
        if (parent) {
            const siblings = parent.querySelectorAll('.menu-item.has-children');
            siblings.forEach(sibling => {
                if (sibling !== menuItem) {
                    sibling.classList.remove('open');
                    const arrow = sibling.querySelector('.menu-arrow');
                    if (arrow) {
                        arrow.style.transform = 'rotate(0deg)';
                    }
                }
            });
        }

        // Toggle current submenu
        if (isOpen) {
            menuItem.classList.remove('open');
            const arrow = element.querySelector('.menu-arrow');
            if (arrow) {
                arrow.style.transform = 'rotate(0deg)';
            }
        } else {
            menuItem.classList.add('open');
            const arrow = element.querySelector('.menu-arrow');
            if (arrow) {
                arrow.style.transform = 'rotate(180deg)';
            }
        }
    };

    // Keyboard navigation support
    document.addEventListener('keydown', function(e) {
        // ESC to close mobile sidebar
        if (e.key === 'Escape') {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && sidebar.classList.contains('mobile-open')) {
                closeMobileSidebar();
            }
        }

        // Alt+S to toggle sidebar (desktop)
        if (e.altKey && e.key === 's' && window.innerWidth > 768) {
            e.preventDefault();
            toggleSidebar();
        }
    });

    // Expose functions globally for use in templates
    window.openMobileSidebar = openMobileSidebar;
    window.closeMobileSidebar = closeMobileSidebar;
    window.toggleSidebar = toggleSidebar;

})();

