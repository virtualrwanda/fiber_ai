document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const signalPowerInput = document.getElementById('signalPower');
    const attenuationInput = document.getElementById('attenuation');
    const distanceInput = document.getElementById('distance');
    const signalPowerValue = document.getElementById('signalPowerValue');
    const attenuationValue = document.getElementById('attenuationValue');
    const distanceValue = document.getElementById('distanceValue');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultAlert = document.getElementById('resultAlert');
    const predictionResult = document.getElementById('predictionResult');
    const probabilityCard = document.getElementById('probabilityCard');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    let probabilityChart = null;

    // Update value displays when sliders change
    signalPowerInput.addEventListener('input', function() {
        signalPowerValue.textContent = `${this.value} dB`;
    });

    attenuationInput.addEventListener('input', function() {
        attenuationValue.textContent = `${this.value} dB/km`;
    });

    distanceInput.addEventListener('input', function() {
        distanceValue.textContent = `${this.value} m`;
    });

    // Analyze button click handler
    analyzeBtn.addEventListener('click', async function() {
        // Show loading overlay
        loadingOverlay.classList.remove('hidden');
        
        // Get input values
        const signalPower = parseFloat(signalPowerInput.value);
        const attenuation = parseFloat(attenuationInput.value);
        const distance = parseFloat(distanceInput.value);
        
        try {
            // Send prediction request
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    signal_power: signalPower,
                    attenuation: attenuation,
                    distance: distance
                }),
            });
            
            if (!response.ok) {
                throw new Error('Prediction request failed');
            }
            
            const data = await response.json();
            
            // Update UI with prediction results
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while analyzing the fiber. Please try again.');
        } finally {
            // Hide loading overlay
            loadingOverlay.classList.add('hidden');
        }
    });
    
    // Function to display prediction results
    function displayResults(data) {
        const prediction = data.prediction;
        const probabilities = data.probabilities;
        
        // Update prediction text
        predictionResult.textContent = prediction;
        
        // Set alert style based on prediction
        resultAlert.className = 'alert';
        
        if (prediction === 'No Fault') {
            resultAlert.classList.add('success');
            resultAlert.querySelector('.alert-icon i').className = 'fas fa-check-circle';
        } else if (prediction === 'Fiber Break') {
            resultAlert.classList.add('danger');
            resultAlert.querySelector('.alert-icon i').className = 'fas fa-exclamation-circle';
        } else if (prediction === 'High Loss') {
            resultAlert.classList.add('warning');
            resultAlert.querySelector('.alert-icon i').className = 'fas fa-exclamation-triangle';
        } else if (prediction === 'Splice Loss') {
            resultAlert.classList.add('info');
            resultAlert.querySelector('.alert-icon i').className = 'fas fa-info-circle';
        }
        
        // Show result alert
        resultAlert.classList.remove('hidden');
        
        // Update probability chart
        updateProbabilityChart(probabilities);
        
        // Show probability card
        probabilityCard.classList.remove('hidden');
    }
    
    // Function to update probability chart
    function updateProbabilityChart(probabilities) {
        const ctx = document.getElementById('probabilityChart').getContext('2d');
        
        // Destroy previous chart if it exists
        if (probabilityChart) {
            probabilityChart.destroy();
        }
        
        // Prepare data for chart
        const labels = Object.keys(probabilities);
        const data = Object.values(probabilities);
        
        // Define colors for each fault type
        const backgroundColors = {
            'No Fault': 'rgba(34, 197, 94, 0.7)',
            'Fiber Break': 'rgba(239, 68, 68, 0.7)',
            'High Loss': 'rgba(245, 158, 11, 0.7)',
            'Splice Loss': 'rgba(59, 130, 246, 0.7)'
        };
        
        const borderColors = {
            'No Fault': 'rgba(34, 197, 94, 1)',
            'Fiber Break': 'rgba(239, 68, 68, 1)',
            'High Loss': 'rgba(245, 158, 11, 1)',
            'Splice Loss': 'rgba(59, 130, 246, 1)'
        };
        
        // Create chart
        probabilityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Probability',
                    data: data,
                    backgroundColor: labels.map(label => backgroundColors[label] || 'rgba(156, 163, 175, 0.7)'),
                    borderColor: labels.map(label => borderColors[label] || 'rgba(156, 163, 175, 1)'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                return `Probability: ${(value * 100).toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                return `${(value * 100).toFixed(0)}%`;
                            }
                        }
                    }
                }
            }
        });
    }
});
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const signalPowerInput = document.getElementById('signalPower');
    const attenuationInput = document.getElementById('attenuation');
    const distanceInput = document.getElementById('distance');
    const signalPowerValue = document.getElementById('signalPowerValue');
    const attenuationValue = document.getElementById('attenuationValue');
    const distanceValue = document.getElementById('distanceValue');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultAlert = document.getElementById('resultAlert');
    const resultText = document.getElementById('resultText');
    const results = document.getElementById('results');
    const loading = document.getElementById('loading');
    
    // Update value displays when sliders change
    signalPowerInput.addEventListener('input', function() {
        signalPowerValue.textContent = `${this.value} dB`;
    });

    attenuationInput.addEventListener('input', function() {
        attenuationValue.textContent = `${this.value} dB/km`;
    });

    distanceInput.addEventListener('input', function() {
        distanceValue.textContent = `${this.value} m`;
    });

    // Analyze button click handler
    analyzeBtn.addEventListener('click', async function() {
        // Show loading, hide button
        loading.classList.remove('hidden');
        analyzeBtn.disabled = true;
        
        // Get input values
        const signalPower = parseFloat(signalPowerInput.value);
        const attenuation = parseFloat(attenuationInput.value);
        const distance = parseFloat(distanceInput.value);
        
        try {
            // Send prediction request
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    signal_power: signalPower,
                    attenuation: attenuation,
                    distance: distance
                }),
            });
            
            if (!response.ok) {
                throw new Error('Prediction request failed');
            }
            
            const data = await response.json();
            
            // Update UI with prediction results
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while analyzing the fiber. Please try again.');
        } finally {
            // Hide loading, enable button
            loading.classList.add('hidden');
            analyzeBtn.disabled = false;
        }
    });
    
    // Function to display prediction results
    function displayResults(data) {
        const prediction = data.prediction;
        const probabilities = data.probabilities;
        const confidence = data.confidence;
        
        // Update result alert
        resultText.innerHTML = `<strong>Detected:</strong> ${prediction}`;
        
        // Set alert style based on prediction
        resultAlert.className = 'alert';
        
        if (prediction === 'No Fault') {
            resultAlert.classList.add('success');
        } else if (prediction === 'Fiber Break') {
            resultAlert.classList.add('danger');
        } else if (prediction === 'High Loss') {
            resultAlert.classList.add('warning');
        } else if (prediction === 'Splice Loss') {
            resultAlert.classList.add('info');
        }
        
        // Show result alert
        resultAlert.classList.remove('hidden');
        
        // Update results text
        let resultsHTML = '<h3>Probabilities:</h3><ul style="list-style: none; margin: 0.5rem 0;">';
        
        for (const [faultType, probability] of Object.entries(probabilities)) {
            const percent = (probability * 100).toFixed(1);
            resultsHTML += `<li>• ${faultType}: ${percent}%</li>`;
        }
        
        resultsHTML += '</ul>';
        
        // Add interpretation
        resultsHTML += '<h3 style="margin-top: 1rem;">Interpretation:</h3>';
        
        if (prediction === 'No Fault') {
            resultsHTML += '<p>The fiber appears to be functioning normally.</p>';
        } else if (prediction === 'Fiber Break') {
            resultsHTML += '<p>The signal power is very low and attenuation is high, indicating a possible fiber break.</p>';
        } else if (prediction === 'High Loss') {
            resultsHTML += '<p>The fiber is experiencing higher than normal attenuation, which could indicate degradation.</p>';
        } else if (prediction === 'Splice Loss') {
            resultsHTML += '<p>There appears to be loss at connection points in the fiber.</p>';
        }
        
        results.innerHTML = resultsHTML;
    }
});