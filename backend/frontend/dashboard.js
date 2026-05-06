// Configuration
const API_BASE = 'http://localhost:8000';
let errorRateChart = null;
let cameraStream = null;
let cameraActive = false;
let lastDetectionId = null;
let lastImageBase64 = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadInitialData();
    setInterval(refreshDashboard, 10000); // Refresh every 10 seconds
    showWelcomeMessage();
});

// Welcome message
function showWelcomeMessage() {
    const resultsDiv = document.getElementById('detectionResults');
    resultsDiv.innerHTML = `
        <div class="text-center p-4">
            <div class="mb-3">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary mx-auto">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M8 14s1.5 2 4 2 4-2 4-2"></path>
                    <line x1="9" y1="9" x2="9.01" y2="9"></line>
                    <line x1="15" y1="9" x2="15.01" y2="9"></line>
                </svg>
            </div>
            <h5 class="text-muted">Willkommen bei SmarTrash!</h5>
            <p class="text-muted">Starte die Kamera oder lade ein Bild hoch, um loszulegen.</p>
        </div>
    `;
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('startCameraBtn').addEventListener('click', startCamera);
    document.getElementById('stopCameraBtn').addEventListener('click', stopCamera);
    document.getElementById('captureBtn').addEventListener('click', captureAndAnalyze);
    document.getElementById('imageUpload').addEventListener('change', handleImageUpload);
    document.getElementById('feedbackYesBtn').addEventListener('click', () => submitFeedback('stimmt'));
    document.getElementById('feedbackNoBtn').addEventListener('click', () => submitFeedback('stimmt_nicht'));
}

// Camera controls - Native Browser API
async function startCamera() {
    try {
        const video = document.getElementById('cameraFeed');
        const overlay = document.getElementById('cameraOverlay');

        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment'
            }
        };

        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = cameraStream;
        await video.play();

        // Hide overlay when camera is active
        if (overlay) {
            overlay.style.display = 'none';
        }

        cameraActive = true;
        document.getElementById('startCameraBtn').disabled = true;
        document.getElementById('stopCameraBtn').disabled = false;
        document.getElementById('captureBtn').disabled = false;

        showAlert('📷 Kamera erfolgreich gestartet!', 'success');
    } catch (error) {
        console.error('Camera error:', error);
        let errorMsg = 'Kamera konnte nicht gestartet werden.';
        if (error.name === 'NotAllowedError') {
            errorMsg = '❌ Kamera-Zugriff verweigert. Bitte erlaube den Zugriff in deinem Browser.';
        } else if (error.name === 'NotFoundError') {
            errorMsg = '❌ Keine Kamera gefunden. Bitte schließe eine Kamera an.';
        }
        showAlert(errorMsg, 'error');
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    const video = document.getElementById('cameraFeed');
    const overlay = document.getElementById('cameraOverlay');
    video.srcObject = null;

    // Show overlay when camera is stopped
    if (overlay) {
        overlay.style.display = 'flex';
    }
    document.getElementById('captureBtn').disabled = true;

    // Clear canvas
    const canvas = document.getElementById('detectionCanvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function captureAndAnalyze() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    lastImageBase64 = canvas.toDataURL('image/jpeg', 0.9);
    analyzeImage(lastImageBase64);
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showAlert('Bitte wähle eine Bilddatei aus.', 'warning');
        return;
    }

    showLoading(true);
    const reader = new FileReader();
    reader.onload = function(e) {
        lastImageBase64 = e.target.result;
        analyzeImage(e.target.result);
    };
    reader.readAsDataURL(file);
}

// Analysis
async function analyzeImage(imageBase64) {
    try {
        // Convert base64 to blob and send as form-data
        const blob = base64ToBlob(imageBase64);
        const formData = new FormData();
        formData.append('file', blob, 'image.jpg');

        const response = await fetch(`${API_BASE}/detect`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const data = await response.json();

        displayDetectionResults(data);
        lastDetectionId = data.detection_id || null;

        // Draw bboxes on canvas
        drawDetections(data.detections);

    } catch (error) {
        console.error('Analysis error:', error);
        showAlert('Fehler bei der Analyse', 'error');
    } finally {
        showLoading(false);
    }
}

function displayDetectionResults(data) {
    const resultsDiv = document.getElementById('detectionResults');
    const feedbackSection = document.getElementById('feedbackSection');

    if (!data.detections || data.detections.length === 0) {
        resultsDiv.innerHTML = `
            <div class="alert alert-warning">
                <strong>🔍 Keine Objekte erkannt</strong>
                <p class="mb-0 mt-2 small">Versuche das Objekt besser zu positionieren oder die Beleuchtung zu verbessern.</p>
            </div>
        `;
        feedbackSection.classList.add('d-none');
        return;
    }

    // Header with count
    let html = `<div class="detection-header mb-3">
        <h4 class="mb-2">✅ ${data.count} Objekt(e) erkannt</h4>
        ${data.battery_warning ? '<div class="alert alert-danger mb-0"><strong>⚠️ Batterie/Elektronik erkannt</strong> → MANUAL REVIEW erforderlich!</div>' : ''}
    </div>`;

    // Detection cards instead of table for better overview
    html += '<div class="detection-results-grid">';

    data.detections.forEach((det, index) => {
        const confidence = (det.confidence * 100).toFixed(1);
        const isManual = det.user_action === 'MANUAL_CHECK_REQUIRED';
        const binIcon = getBinIcon(det.recommended_bin);
        const confidenceClass = confidence >= 80 ? 'success' : confidence >= 50 ? 'warning' : 'danger';

        html += `
            <div class="detection-card ${isManual ? 'border-warning' : 'border-success'}">
                <div class="detection-card-header">
                    <span class="detection-number">#${index + 1}</span>
                    <span class="badge bg-${confidenceClass}">${confidence}%</span>
                </div>
                <div class="detection-card-body">
                    <h5 class="detection-class-name">${det.class_name}</h5>
                    <div class="detection-bin">
                        <span class="bin-icon">${binIcon}</span>
                        <span class="bin-name">${det.recommended_bin || 'Keine Empfehlung'}</span>
                    </div>
                </div>
                <div class="detection-card-footer">
                    ${isManual ?
                        '<span class="badge bg-warning w-100 py-2">👤 MANUELLE PRÜFUNG</span>' :
                        '<span class="badge bg-success w-100 py-2">✅ AUTO-SORTIERUNG</span>'
                    }
                </div>
            </div>
        `;
    });

    html += '</div>';

    // Show quality control info
    if (data.adaptive_policy_mode) {
        const modeEmoji = {
            'cold_start_safe': '🔵',
            'strict_recovery': '🟡',
            'stable_high_quality': '🟢'
        };
        html += `<div class="alert alert-info mt-3">
            <small><strong>${modeEmoji[data.adaptive_policy_mode] || '⚙️'} Quality Mode:</strong> ${data.adaptive_policy_mode}</small>
        </div>`;
    }

    resultsDiv.innerHTML = html;
    feedbackSection.classList.remove('d-none');
}

function getBinIcon(binName) {
    const icons = {
        'Restmüll': '🗑️',
        'Wertstoff': '♻️',
        'Papier': '📄',
        'Bio': '🌱'
    };
    return icons[binName] || '❓';
}

function drawDetections(detections) {
    const canvas = document.getElementById('detectionCanvas');
    const ctx = canvas.getContext('2d');

    const video = document.getElementById('cameraFeed');
    canvas.width = video.videoWidth || video.clientWidth || 640;
    canvas.height = video.videoHeight || video.clientHeight || 480;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach((det, index) => {
        const [x1, y1, x2, y2] = det.bbox;
        const isManual = det.user_action === 'MANUAL_CHECK_REQUIRED';

        // Box styling
        ctx.strokeStyle = isManual ? '#ffc107' : '#00ff00';
        ctx.lineWidth = 3;
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 4;

        // Draw box
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Label background
        const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`;
        ctx.font = 'bold 16px Arial';
        const textWidth = ctx.measureText(label).width;

        ctx.fillStyle = isManual ? '#ffc107' : '#00ff00';
        ctx.fillRect(x1, y1 - 28, textWidth + 12, 26);

        // Label text
        ctx.fillStyle = '#000';
        ctx.fillText(label, x1 + 6, y1 - 8);

        // Number badge
        ctx.fillStyle = isManual ? '#ffc107' : '#00ff00';
        ctx.beginPath();
        ctx.arc(x1 - 12, y1 - 12, 16, 0, 2 * Math.PI);
        ctx.fill();

        ctx.fillStyle = '#000';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${index + 1}`, x1 - 12, y1 - 7);
        ctx.textAlign = 'left';

        ctx.shadowBlur = 0;
    });
}

// Feedback
async function submitFeedback(feedback_type) {
    if (!lastDetectionId) {
        showAlert('Keine Detektion zur Bewertung vorhanden', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/feedback/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                detection_id: lastDetectionId,
                feedback_type: feedback_type,
                image_base64: lastImageBase64
            })
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const data = await response.json();

        showAlert(`Feedback gespeichert: ${feedback_type}`, 'success');
        document.getElementById('feedbackSection').classList.add('d-none');
        refreshDashboard();

    } catch (error) {
        console.error('Feedback error:', error);
        showAlert('Fehler beim Speichern des Feedbacks', 'error');
    }
}

// Dashboard refresh
async function loadInitialData() {
    await Promise.all([
        loadComplianceStatus(),
        loadQualityControl(),
        loadErrorRateTrend(),
        loadReviewQueue()
    ]);
}

async function refreshDashboard() {
    await Promise.all([
        checkSystemHealth(),
        loadErrorRateTrend(),
        loadReviewQueue()
    ]);
}

async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            document.getElementById('healthStatus').textContent = '🟢 Online';
            document.getElementById('healthStatus').className = 'badge bg-success';
        }
    } catch (error) {
        document.getElementById('healthStatus').textContent = '🔴 Offline';
        document.getElementById('healthStatus').className = 'badge bg-danger';
    }
}

async function loadComplianceStatus() {
    try {
        const response = await fetch(`${API_BASE}/compliance/report`);
        if (!response.ok) return;

        const data = await response.json();
        const score = (data.score * 100).toFixed(0);

        document.getElementById('complianceScore').textContent = `✅ ${score}%`;
        document.getElementById('complianceScore').className = data.compliant
            ? 'badge bg-success'
            : 'badge bg-danger';

        let html = `<div class="mb-3">
            <div class="progress mb-2">
                <div class="progress-bar ${data.compliant ? 'bg-success' : 'bg-danger'}"
                     style="width: ${score}%">${score}%</div>
            </div>
        </div>`;

        data.checks?.forEach(check => {
            const icon = check.ok ? '✅' : '❌';
            html += `<div class="d-flex justify-content-between mb-2">
                <span>${check.name}:</span>
                <span class="badge ${check.ok ? 'bg-success' : 'bg-danger'}">${icon}</span>
            </div>`;
        });

        document.getElementById('complianceDetails').innerHTML = html;

    } catch (error) {
        console.error('Compliance load error:', error);
    }
}

async function loadQualityControl() {
    try {
        const response = await fetch(`${API_BASE}/quality/control`);
        if (!response.ok) return;

        const data = await response.json();

        let html = `<div class="small">
            <div class="mb-2">
                <strong>Mode:</strong>
                <span class="badge bg-info">${data.mode || 'unknown'}</span>
            </div>
            <div class="mb-2">
                <strong>Min Quality:</strong> ${(data.min_quality * 100).toFixed(0)}%
            </div>
            <div class="mb-2">
                <strong>Min Confidence:</strong> ${(data.min_confidence * 100).toFixed(0)}%
            </div>
        </div>`;

        document.getElementById('qualityControlMode').innerHTML = html;

    } catch (error) {
        console.error('Quality control load error:', error);
    }
}

async function loadErrorRateTrend() {
    try {
        const response = await fetch(`${API_BASE}/quality/error-trend`);
        if (!response.ok) return;

        const data = await response.json();

        // Update chart
        updateErrorRateChart(data);

        // Update stats
        const recentErrorRate = (data.recent_error_rate * 100).toFixed(1);
        const trend = data.trend || 'stable';
        const trendIcon = trend === 'improving' ? '📈' : trend === 'worsening' ? '📉' : '➡️';

        document.getElementById('errorRateStats').innerHTML = `
            <div class="d-flex justify-content-between">
                <span>Recent Error Rate:</span>
                <strong>${recentErrorRate}%</strong>
            </div>
            <div class="d-flex justify-content-between">
                <span>Trend:</span>
                <strong>${trendIcon} ${trend}</strong>
            </div>
            <div class="d-flex justify-content-between">
                <span>Samples:</span>
                <strong>${data.samples || 0}</strong>
            </div>
        `;

    } catch (error) {
        console.error('Error rate load error:', error);
    }
}

function updateErrorRateChart(data) {
    const ctx = document.getElementById('errorRateChart').getContext('2d');

    const labels = Array(data.samples || 10).fill(0).map((_, i) => `${i}`);
    const dataPoints = Array(data.samples || 10).fill(data.overall_error_rate || 0);

    if (errorRateChart) {
        errorRateChart.destroy();
    }

    errorRateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Error Rate',
                data: dataPoints,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 3
            }, {
                label: 'Target',
                data: Array(labels.length).fill(0.15),
                borderColor: '#28a745',
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 1,
                    ticks: {
                        callback: function(value) {
                            return (value * 100).toFixed(0) + '%';
                        }
                    }
                }
            }
        }
    });
}

async function loadReviewQueue() {
    try {
        const response = await fetch(`${API_BASE}/learning/review-queue`);
        if (!response.ok) return;

        const data = response.json().then(d => d.cases || []);
        const cases = await data;

        const queueHeader = document.querySelector('.card-header.bg-danger h5');
        queueHeader.textContent = `🎓 Review-Queue (${cases.length})`;

        if (cases.length === 0) {
            document.getElementById('reviewQueue').innerHTML =
                '<p class="text-success text-center"><strong>✅ Keine Cases zur Review!</strong></p>';
            return;
        }

        let html = '';
        cases.slice(0, 10).forEach((cas, idx) => {
            html += `<div class="mb-2 p-2 bg-light rounded small">
                <div><strong>Case ${idx + 1}:</strong> ${cas.class_name}</div>
                <div class="text-muted">ID: ${cas.detection_id.substring(0, 8)}...</div>
            </div>`;
        });

        document.getElementById('reviewQueue').innerHTML = html;

    } catch (error) {
        console.error('Review queue load error:', error);
    }
}

// Utilities
function showLoading(show) {
    document.getElementById('loadingSpinner').classList.toggle('d-none', !show);
}

function showAlert(message, type = 'info') {
    const alertHtml = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;

    const container = document.querySelector('.container-fluid');
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => alertDiv.remove(), 5000);
}

function base64ToBlob(base64) {
    const parts = base64.split(';base64,');
    const contentType = parts[0].split(':')[1];
    const raw = window.atob(parts[1]);
    const rawLength = raw.length;
    const uInt8Array = new Uint8Array(rawLength);

    for (let i = 0; i < rawLength; ++i) {
        uInt8Array[i] = raw.charCodeAt(i);
    }

    return new Blob([uInt8Array], { type: contentType });
}
