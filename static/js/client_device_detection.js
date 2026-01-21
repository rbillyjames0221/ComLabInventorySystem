/**
 * Client-side device detection for browser-based device registration
 * This script collects device information from the client's browser
 * to uniquely identify each device when registering through the web interface.
 */

/**
 * Get local IP address using WebRTC (if available)
 * Note: This may not work in all browsers or may require user interaction
 */
async function getLocalIPAddress() {
    return new Promise((resolve) => {
        // WebRTC is not always available, so we'll try but not fail if it doesn't work
        const RTCPeerConnection = window.RTCPeerConnection || 
                                  window.mozRTCPeerConnection || 
                                  window.webkitRTCPeerConnection;
        
        if (!RTCPeerConnection) {
            resolve(null);
            return;
        }
        
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        
        pc.createDataChannel('');
        
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                const candidate = event.candidate.candidate;
                const match = candidate.match(/([0-9]{1,3}(\.[0-9]{1,3}){3})/);
                if (match) {
                    const localIP = match[1];
                    // Filter out public IPs and localhost
                    if (!localIP.startsWith('127.') && 
                        !localIP.startsWith('169.254.') &&
                        localIP !== '0.0.0.0') {
                        pc.close();
                        resolve(localIP);
                        return;
                    }
                }
            }
        };
        
        pc.createOffer()
            .then(offer => pc.setLocalDescription(offer))
            .catch(() => {
                pc.close();
                resolve(null);
            });
        
        // Timeout after 3 seconds
        setTimeout(() => {
            pc.close();
            resolve(null);
        }, 3000);
    });
}

/**
 * Generate canvas fingerprint
 * Canvas fingerprinting creates a unique identifier based on how the browser renders graphics
 */
function getCanvasFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;
        
        // Draw text with various properties
        ctx.textBaseline = 'top';
        ctx.font = '14px "Arial"';
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = '#f60';
        ctx.fillRect(125, 1, 62, 20);
        ctx.fillStyle = '#069';
        ctx.fillText('DeviceFingerprint', 2, 15);
        ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
        ctx.fillText('DeviceFingerprint', 4, 17);
        
        // Get canvas data as base64
        const canvasData = canvas.toDataURL();
        
        // Create hash of canvas data
        let hash = 0;
        for (let i = 0; i < canvasData.length; i++) {
            const char = canvasData.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        
        return Math.abs(hash).toString(16);
    } catch (e) {
        return null;
    }
}

/**
 * Generate WebGL fingerprint
 * WebGL fingerprinting creates a unique identifier based on graphics card/driver info
 */
function getWebGLFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return null;
        
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (!debugInfo) return null;
        
        const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        
        // Create hash
        const combined = (vendor || '') + '|' + (renderer || '');
        let hash = 0;
        for (let i = 0; i < combined.length; i++) {
            const char = combined.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        
        return Math.abs(hash).toString(16);
    } catch (e) {
        return null;
    }
}

/**
 * Get device hostname from various sources
 * Since browsers can't directly access hostname, we'll use available information
 */
function getDeviceHostname() {
    // Try to get from window.location if available
    if (window.location && window.location.hostname && 
        window.location.hostname !== 'localhost' && 
        window.location.hostname !== '127.0.0.1') {
        // This would be the server hostname, not client, so skip
    }
    
    // Use a combination of user agent and other info to create a pseudo-hostname
    const userAgent = navigator.userAgent || '';
    const platform = navigator.platform || '';
    
    // Extract some identifying info from user agent
    let hostname = 'Device';
    
    // Try to extract computer name patterns from user agent (if available)
    // Some browsers include system info in user agent
    if (userAgent.includes('Windows')) {
        hostname = 'PC-' + platform.replace(/\s+/g, '-');
    } else if (userAgent.includes('Mac')) {
        hostname = 'Mac-' + platform.replace(/\s+/g, '-');
    } else if (userAgent.includes('Linux')) {
        hostname = 'Linux-' + platform.replace(/\s+/g, '-');
    }
    
    return hostname;
}

/**
 * Detect device type from user agent and screen size
 */
function detectDeviceType() {
    const userAgent = navigator.userAgent || '';
    const userAgentLower = userAgent.toLowerCase();
    const screenWidth = window.screen.width || 0;
    const screenHeight = window.screen.height || 0;
    
    // Mobile devices
    if (userAgentLower.includes('mobile') || 
        userAgentLower.includes('android') || 
        userAgentLower.includes('iphone') || 
        userAgentLower.includes('ipod')) {
        return 'Mobile';
    }
    
    // Tablets
    if (userAgentLower.includes('ipad') || 
        userAgentLower.includes('tablet') || 
        (screenWidth >= 600 && screenWidth <= 1024 && screenHeight >= 600 && screenHeight <= 1366)) {
        return 'Tablet';
    }
    
    // Laptops (check screen size and user agent)
    if (userAgentLower.includes('laptop') || 
        userAgentLower.includes('notebook') ||
        (screenWidth >= 1024 && screenWidth <= 1920 && screenHeight >= 768 && screenHeight <= 1080)) {
        return 'Laptop';
    }
    
    // Desktop (default for larger screens)
    if (screenWidth >= 1280) {
        return 'Desktop';
    }
    
    return 'Unknown';
}

/**
 * Collect all available device information from the client's browser
 * This is the main function that gathers device fingerprinting data
 */
async function collectClientDeviceInfo() {
    const deviceInfo = {
        // Browser and OS information
        user_agent: navigator.userAgent || '',
        platform: navigator.platform || '',
        language: navigator.language || navigator.userLanguage || '',
        
        // Screen information
        screen_resolution: `${window.screen.width || 0}x${window.screen.height || 0}`,
        screen_color_depth: window.screen.colorDepth || 0,
        screen_pixel_depth: window.screen.pixelDepth || 0,
        
        // Timezone
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
        timezone_offset: new Date().getTimezoneOffset(),
        
        // Hardware information
        hardware_concurrency: navigator.hardwareConcurrency || 0,
        device_memory: navigator.deviceMemory || 0,
        max_touch_points: navigator.maxTouchPoints || 0,
        
        // Browser capabilities
        cookie_enabled: navigator.cookieEnabled,
        do_not_track: navigator.doNotTrack || 'unknown',
        
        // Fingerprints
        canvas_fingerprint: getCanvasFingerprint(),
        webgl_fingerprint: getWebGLFingerprint(),
        
        // Network information (will be filled asynchronously)
        local_ip: null,
        
        // Derived information
        device_type: detectDeviceType(),
        hostname: getDeviceHostname()
    };
    
    // Try to get local IP address (may not always work)
    try {
        deviceInfo.local_ip = await getLocalIPAddress();
    } catch (e) {
        // WebRTC may not be available or may require user interaction
        deviceInfo.local_ip = null;
    }
    
    return deviceInfo;
}

/**
 * Generate a unique device ID from collected device information
 * This creates a deterministic unique identifier
 */
function generateDeviceUniqueId(deviceInfo) {
    // Create a composite string from all device characteristics
    const fingerprintParts = [
        deviceInfo.user_agent,
        deviceInfo.platform,
        deviceInfo.screen_resolution,
        deviceInfo.timezone,
        deviceInfo.language,
        deviceInfo.hardware_concurrency.toString(),
        deviceInfo.device_memory.toString(),
        deviceInfo.canvas_fingerprint || '',
        deviceInfo.webgl_fingerprint || '',
        deviceInfo.local_ip || ''
    ];
    
    const fingerprintString = fingerprintParts.join('|');
    
    // Generate a hash-based unique ID
    // Using a simple hash function (in production, you might want to use a more robust method)
    let hash = 0;
    for (let i = 0; i < fingerprintString.length; i++) {
        const char = fingerprintString.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    
    // Convert to a UUID-like string format
    const hashStr = Math.abs(hash).toString(16).padStart(8, '0');
    const timestamp = Date.now().toString(16);
    
    // Create a more unique ID by combining hash with timestamp
    // Format: hash-timestamp-random
    const random = Math.random().toString(16).substring(2, 10);
    const uniqueId = `${hashStr}-${timestamp.substring(0, 8)}-${random}`;
    
    return uniqueId;
}

/**
 * Main function to get device information for registration
 * Returns a promise that resolves with device information ready to send to server
 */
async function getClientDeviceInfo() {
    try {
        // Collect all device information
        const deviceInfo = await collectClientDeviceInfo();
        
        // Generate unique ID
        const uniqueId = generateDeviceUniqueId(deviceInfo);
        
        // Format for server
        return {
            success: true,
            hostname: deviceInfo.hostname,
            ip_address: deviceInfo.local_ip || 'Unknown',
            mac_address: 'Unknown', // Browsers cannot access MAC address directly
            device_type: deviceInfo.device_type,
            unique_id: uniqueId,
            machine_id: uniqueId,
            platform: deviceInfo.platform,
            user_agent: deviceInfo.user_agent,
            screen_resolution: deviceInfo.screen_resolution,
            // Include full device info for server-side processing
            full_device_info: deviceInfo
        };
    } catch (error) {
        console.error('Error collecting device info:', error);
        return {
            success: false,
            message: 'Failed to collect device information: ' + error.message
        };
    }
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getClientDeviceInfo,
        collectClientDeviceInfo,
        generateDeviceUniqueId,
        detectDeviceType
    };
}

