// Content Research Pipeline - Frontend Application
// Handles UI interactions and API communication

// State management
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const settingsModal = document.getElementById('settingsModal');
const settingsBtn = document.getElementById('settingsBtn');
const closeBtn = document.querySelector('.close');
const saveKeysBtn = document.getElementById('saveKeysBtn');
const clearKeysBtn = document.getElementById('clearKeysBtn');
const startBtn = document.getElementById('startBtn');
const queryInput = document.getElementById('queryInput');
const statusSection = document.getElementById('statusSection');

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    attachEventListeners();
    checkRequiredKeys();
});

// Event Listeners
function attachEventListeners() {
    // Settings modal
    settingsBtn.onclick = () => openSettings();
    closeBtn.onclick = () => closeSettings();
    saveKeysBtn.onclick = () => saveSettings();
    clearKeysBtn.onclick = () => clearSettings();
    
    // Close modal when clicking outside
    window.onclick = (event) => {
        if (event.target === settingsModal) {
            closeSettings();
        }
    };
    
    // Start research button
    startBtn.onclick = () => startResearch();
    
    // Allow Enter key in textarea (Ctrl+Enter to submit)
    queryInput.onkeydown = (event) => {
        if (event.ctrlKey && event.key === 'Enter') {
            startResearch();
        }
    };
}

// Settings Management
function openSettings() {
    settingsModal.style.display = 'block';
}

function closeSettings() {
    settingsModal.style.display = 'none';
}

function loadSettings() {
    document.getElementById('openaiKey').value = localStorage.getItem('openai_api_key') || '';
    document.getElementById('googleApiKey').value = localStorage.getItem('google_api_key') || '';
    document.getElementById('googleCseId').value = localStorage.getItem('google_cse_id') || '';
    document.getElementById('pipelineApiKey').value = localStorage.getItem('pipeline_api_key') || '';
}

function saveSettings() {
    const openaiKey = document.getElementById('openaiKey').value.trim();
    const googleApiKey = document.getElementById('googleApiKey').value.trim();
    const googleCseId = document.getElementById('googleCseId').value.trim();
    const pipelineApiKey = document.getElementById('pipelineApiKey').value.trim();
    
    // Validate required fields
    if (!openaiKey || !googleApiKey || !googleCseId) {
        alert('Please fill in all required fields (OpenAI API Key, Google API Key, and Google CSE ID).');
        return;
    }
    
    // Save to localStorage
    localStorage.setItem('openai_api_key', openaiKey);
    localStorage.setItem('google_api_key', googleApiKey);
    localStorage.setItem('google_cse_id', googleCseId);
    localStorage.setItem('pipeline_api_key', pipelineApiKey);
    
    closeSettings();
    checkRequiredKeys();
    showNotification('Settings saved successfully!', 'success');
}

function clearSettings() {
    if (confirm('Are you sure you want to clear all saved API keys?')) {
        localStorage.removeItem('openai_api_key');
        localStorage.removeItem('google_api_key');
        localStorage.removeItem('google_cse_id');
        localStorage.removeItem('pipeline_api_key');
        loadSettings();
        checkRequiredKeys();
        showNotification('All settings cleared.', 'info');
    }
}

function checkRequiredKeys() {
    const hasKeys = localStorage.getItem('openai_api_key') && 
                    localStorage.getItem('google_api_key') && 
                    localStorage.getItem('google_cse_id');
    
    startBtn.disabled = !hasKeys;
    
    if (!hasKeys) {
        startBtn.textContent = '⚠️ Configure API Keys First';
    } else {
        startBtn.textContent = 'Start Research';
    }
}

// Research Pipeline Functions
async function startResearch() {
    const query = queryInput.value.trim();
    
    if (!query) {
        alert('Please enter a research query.');
        return;
    }
    
    // Get API keys from localStorage
    const openaiKey = localStorage.getItem('openai_api_key');
    const googleApiKey = localStorage.getItem('google_api_key');
    const googleCseId = localStorage.getItem('google_cse_id');
    const pipelineApiKey = localStorage.getItem('pipeline_api_key');
    
    if (!openaiKey || !googleApiKey || !googleCseId) {
        alert('Please configure your API keys in Settings first.');
        openSettings();
        return;
    }
    
    // Get options
    const includeImages = document.getElementById('includeImages').checked;
    const includeVideos = document.getElementById('includeVideos').checked;
    const includeNews = document.getElementById('includeNews').checked;
    
    // Disable start button
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner"></span> Starting...';
    
    try {
        // Prepare request body
        const requestBody = {
            query: query,
            include_images: includeImages,
            include_videos: includeVideos,
            include_news: includeNews,
            openai_api_key: openaiKey,
            google_api_key: googleApiKey,
            google_cse_id: googleCseId
        };
        
        // Prepare headers
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add pipeline API key if provided
        if (pipelineApiKey) {
            headers['X-API-Key'] = pipelineApiKey;
        }
        
        // Call API
        const response = await fetch('/research', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start research');
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        // Show status section
        showStatusSection(data.job_id, query);
        
        // Start polling for status
        startPolling(data.job_id);
        
    } catch (error) {
        console.error('Error starting research:', error);
        showNotification(`Error: ${error.message}`, 'error');
        startBtn.disabled = false;
        startBtn.textContent = 'Start Research';
    }
}

function showStatusSection(jobId, query) {
    statusSection.style.display = 'block';
    document.getElementById('jobId').textContent = `Job ID: ${jobId}`;
    document.getElementById('statusText').textContent = 'Pending';
    document.getElementById('statusText').className = 'status-badge pending';
    document.getElementById('statusMessage').textContent = `Researching: "${query}"`;
    document.getElementById('progress').style.width = '10%';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
    
    // Scroll to status section
    statusSection.scrollIntoView({ behavior: 'smooth' });
}

function startPolling(jobId) {
    // Clear any existing interval
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // Poll every 3 seconds
    pollInterval = setInterval(() => {
        pollStatus(jobId);
    }, 3000);
    
    // Poll immediately
    pollStatus(jobId);
}

async function pollStatus(jobId) {
    try {
        // Prepare headers
        const headers = {};
        const pipelineApiKey = localStorage.getItem('pipeline_api_key');
        if (pipelineApiKey) {
            headers['X-API-Key'] = pipelineApiKey;
        }
        
        const response = await fetch(`/status/${jobId}`, {
            headers: headers
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const data = await response.json();
        updateUI(data);
        
    } catch (error) {
        console.error('Error polling status:', error);
        // Don't show error notification for polling failures - just log them
    }
}

function updateUI(statusData) {
    const status = statusData.status;
    const statusText = document.getElementById('statusText');
    const statusMessage = document.getElementById('statusMessage');
    const progress = document.getElementById('progress');
    
    // Update status badge
    statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusText.className = `status-badge ${status}`;
    
    // Update progress bar and message based on status
    let progressPercent = 10;
    let message = '';
    
    switch (status) {
        case 'pending':
            progressPercent = 10;
            message = 'Job is queued and waiting to start...';
            break;
        case 'running':
            progressPercent = 50;
            message = 'Research pipeline is running. This may take a few minutes...';
            break;
        case 'completed':
            progressPercent = 100;
            message = 'Research completed successfully!';
            stopPolling();
            showResults(statusData);
            break;
        case 'failed':
            progressPercent = 100;
            message = 'Research failed.';
            stopPolling();
            showError(statusData.error || 'An unknown error occurred.');
            break;
        default:
            progressPercent = 50;
            message = `Status: ${status}`;
    }
    
    progress.style.width = `${progressPercent}%`;
    statusMessage.textContent = message;
}

function showResults(statusData) {
    const resultSection = document.getElementById('resultSection');
    const reportLink = document.getElementById('reportLink');
    
    resultSection.style.display = 'block';
    
    if (statusData.report_url) {
        reportLink.href = statusData.report_url;
        reportLink.style.display = 'inline-block';
    } else {
        reportLink.style.display = 'none';
    }
    
    // Re-enable start button
    startBtn.disabled = false;
    startBtn.textContent = 'Start Research';
    
    showNotification('Research completed successfully!', 'success');
}

function showError(errorMessage) {
    const errorSection = document.getElementById('errorSection');
    const errorMessageEl = document.getElementById('errorMessage');
    
    errorSection.style.display = 'block';
    errorMessageEl.textContent = errorMessage;
    
    // Re-enable start button
    startBtn.disabled = false;
    startBtn.textContent = 'Start Research';
    
    showNotification('Research failed. Please try again.', 'error');
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 2000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    // Set color based on type
    switch (type) {
        case 'success':
            notification.style.background = '#d4edda';
            notification.style.color = '#155724';
            notification.style.border = '1px solid #c3e6cb';
            break;
        case 'error':
            notification.style.background = '#f8d7da';
            notification.style.color = '#721c24';
            notification.style.border = '1px solid #f5c6cb';
            break;
        case 'info':
        default:
            notification.style.background = '#d1ecf1';
            notification.style.color = '#0c5460';
            notification.style.border = '1px solid #bee5eb';
    }
    
    // Add to document
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 4000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
