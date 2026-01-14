/**
 * Login Page JavaScript
 * Handles form validation, UX enhancements, and notifications
 */

(function() {
    'use strict';

    // DOM Elements
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('togglePassword');
    const submitBtn = document.getElementById('submitBtn');
    const notify = document.getElementById('notify');
    const notifyMessage = document.getElementById('notify-message');
    const closeBtn = document.getElementById('notify-close');

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        initFormValidation();
        initPasswordToggle();
        initNotifications();
        initAccessibility();
        displayFlashMessages();
    });

    /**
     * Initialize form validation
     */
    function initFormValidation() {
        if (!loginForm) return;

        // Real-time validation
        usernameInput.addEventListener('blur', validateUsername);
        passwordInput.addEventListener('blur', validatePassword);
        usernameInput.addEventListener('input', clearError);
        passwordInput.addEventListener('input', clearError);

        // Form submission
        loginForm.addEventListener('submit', handleFormSubmit);
    }

    /**
     * Validate username
     */
    function validateUsername() {
        const username = usernameInput.value.trim();
        const errorEl = document.getElementById('username-error');

        if (!username) {
            showFieldError('username', 'Username is required');
            return false;
        }

        if (username.length < 3) {
            showFieldError('username', 'Username must be at least 3 characters');
            return false;
        }

        clearFieldError('username');
        return true;
    }

    /**
     * Validate password
     */
    function validatePassword() {
        const password = passwordInput.value;
        const errorEl = document.getElementById('password-error');

        if (!password) {
            showFieldError('password', 'Password is required');
            return false;
        }

        if (password.length < 8) {
            showFieldError('password', 'Password must be at least 8 characters');
            return false;
        }

        clearFieldError('password');
        return true;
    }

    /**
     * Show field error
     */
    function showFieldError(fieldName, message) {
        const errorEl = document.getElementById(`${fieldName}-error`);
        const inputEl = document.getElementById(fieldName);
        
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
        
        if (inputEl) {
            inputEl.setAttribute('aria-invalid', 'true');
            inputEl.classList.add('error');
        }
    }

    /**
     * Clear field error
     */
    function clearFieldError(fieldName) {
        const errorEl = document.getElementById(`${fieldName}-error`);
        const inputEl = document.getElementById(fieldName);
        
        if (errorEl) {
            errorEl.textContent = '';
            errorEl.style.display = 'none';
        }
        
        if (inputEl) {
            inputEl.setAttribute('aria-invalid', 'false');
            inputEl.classList.remove('error');
        }
    }

    /**
     * Clear error on input
     */
    function clearError(e) {
        const fieldName = e.target.id;
        clearFieldError(fieldName);
    }

    /**
     * Handle form submission
     */
    function handleFormSubmit(e) {
        e.preventDefault();

        // Validate all fields
        const isUsernameValid = validateUsername();
        const isPasswordValid = validatePassword();

        if (!isUsernameValid || !isPasswordValid) {
            showNotification('Please fix the errors before submitting.', 'error');
            // Focus on first invalid field
            if (!isUsernameValid) {
                usernameInput.focus();
            } else if (!isPasswordValid) {
                passwordInput.focus();
            }
            return;
        }

        // Show loading state
        setLoadingState(true);

        // Submit form
        loginForm.submit();
    }

    /**
     * Set loading state
     */
    function setLoadingState(loading) {
        if (loading) {
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
            submitBtn.setAttribute('aria-busy', 'true');
        } else {
            submitBtn.disabled = false;
            submitBtn.classList.remove('loading');
            submitBtn.setAttribute('aria-busy', 'false');
        }
    }

    /**
     * Initialize password toggle
     */
    function initPasswordToggle() {
        if (!togglePasswordBtn || !passwordInput) return;

        togglePasswordBtn.addEventListener('click', function() {
            const isPassword = passwordInput.getAttribute('type') === 'password';
            const newType = isPassword ? 'text' : 'password';
            passwordInput.setAttribute('type', newType);
            
            const icon = togglePasswordBtn.querySelector('i');
            if (icon) {
                // Remove both classes first to ensure only one icon shows
                icon.classList.remove('fa-eye', 'fa-eye-slash');
                // When password is visible (text), show eye-slash (click to hide)
                // When password is hidden (password), show eye (click to show)
                if (newType === 'text') {
                    icon.classList.add('fa-eye-slash');
                } else {
                    icon.classList.add('fa-eye');
                }
            }
            
            togglePasswordBtn.setAttribute('aria-label', 
                newType === 'password' ? 'Show password' : 'Hide password'
            );
        });

        // Keyboard support
        togglePasswordBtn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                togglePasswordBtn.click();
            }
        });
    }

    /**
     * Initialize notifications
     */
    function initNotifications() {
        if (!closeBtn) return;

        closeBtn.addEventListener('click', function() {
            hideNotification();
        });

        // Auto-hide after 5 seconds
        if (notify.classList.contains('show')) {
            setTimeout(hideNotification, 5000);
        }
    }

    /**
     * Show notification
     */
    function showNotification(message, type = 'error') {
        if (!notify || !notifyMessage) return;

        notifyMessage.textContent = message;
        notify.className = `notification ${type} show`;
        notify.setAttribute('role', 'alert');
        notify.setAttribute('aria-live', 'polite');

        // Auto-hide after 5 seconds
        setTimeout(hideNotification, 5000);

        // Focus management for accessibility
        notify.focus();
    }

    /**
     * Hide notification
     */
    function hideNotification() {
        if (!notify) return;
        notify.classList.remove('show');
        notify.removeAttribute('role');
    }

    /**
     * Display Flask flash messages
     */
    function displayFlashMessages() {
        // Check for flash messages from server
        const flashMessages = document.querySelectorAll('[data-flash-message]');
        flashMessages.forEach(function(el) {
            const message = el.getAttribute('data-flash-message');
            const type = el.getAttribute('data-flash-type') || 'error';
            showNotification(message, type);
        });

        // Also check for messages in URL (for redirects)
        const urlParams = new URLSearchParams(window.location.search);
        const flashMsg = urlParams.get('flash');
        const flashType = urlParams.get('type') || 'error';
        if (flashMsg) {
            showNotification(decodeURIComponent(flashMsg), flashType);
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }

    /**
     * Initialize accessibility features
     */
    function initAccessibility() {
        // Add ARIA labels if missing
        if (usernameInput && !usernameInput.getAttribute('aria-label')) {
            usernameInput.setAttribute('aria-label', 'Username');
        }
        if (passwordInput && !passwordInput.getAttribute('aria-label')) {
            passwordInput.setAttribute('aria-label', 'Password');
        }

        // Keyboard navigation for form
        loginForm.addEventListener('keydown', function(e) {
            // Submit on Enter key (when not in textarea)
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                if (e.target.type !== 'submit') {
                    e.preventDefault();
                    handleFormSubmit(e);
                }
            }
        });

        // Announce errors to screen readers
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const errorEl = mutation.target;
                    if (errorEl.classList && errorEl.classList.contains('error-message') && errorEl.textContent) {
                        // Error is already announced via aria-describedby
                        // But we can add a live region for dynamic updates
                        const liveRegion = document.createElement('div');
                        liveRegion.setAttribute('role', 'status');
                        liveRegion.setAttribute('aria-live', 'polite');
                        liveRegion.className = 'sr-only';
                        liveRegion.textContent = errorEl.textContent;
                        document.body.appendChild(liveRegion);
                        setTimeout(function() {
                            document.body.removeChild(liveRegion);
                        }, 1000);
                    }
                }
            });
        });

        // Observe error messages
        const errorMessages = document.querySelectorAll('.error-message');
        errorMessages.forEach(function(el) {
            observer.observe(el, { childList: true, characterData: true, subtree: true });
        });
    }

    // Expose showNotification for use in templates
    window.showNotification = showNotification;

})();

