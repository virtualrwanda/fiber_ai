document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    let faultDistributionChart = null;
    let signalPowerChart = null;
    
    // Load dashboard data
    loadDashboardData();
    
    // Refresh data every 30 seconds
    setInterval(loadDashboardData, 30000);
    
    async function loadDashboardData() {
        try {
            // Load statistics
            const statsResponse = await fetch('/api/data/stats');
            if (statsResponse.ok) {
                const statsData = await statsResponse.json();
                updateStats(statsData);
                updateFaultDistributionChart(statsData.fault_distribution);
            }
            
            // Load recent measurements
            const measurementsResponse = await fetch('/api/data/recent?limit=20');
            if (measurementsResponse.ok) {
                const measurementsData = await measurementsResponse.json();
                updateRecentMeasurements(measurementsData);
                updateSignalPowerChart(measurementsData);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }
    
    function updateStats(data) {
        document.getElementById('deviceCount').textContent = data.device_count;
        document.getElementById('measurementCount').textContent = data.measurement_count;
        
        // Calculate fault rate
        const totalFaults = Object.entries(data.fault_distribution)
            .filter(([type, _]) => type !== 'No Fault')
            .reduce((sum, [_, count]) => sum + count, 0);
        
        const totalMeasurements = data.measurement_count;
        const faultRate = totalMeasurements > 0 ? (totalFaults / totalMeasurements * 100).toFixed(1) + '%' : '0%';
        
        document.getElementById('faultRate').textContent = faultRate;
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
    }
    
    function updateFaultDistributionChart(faultDistribution) {
        const ctx = document.getElementById('faultDistributionChart').getContext('2d');
        
        // Destroy previous chart if it exists
        if (faultDistributionChart) {
            faultDistributionChart.destroy();
        }
        
        // Prepare data for chart
        const labels = Object.keys(faultDistribution);
        const data = Object.values(faultDistribution);
        
        // Define colors for each fault type
        const backgroundColors = {
            'No Fault': 'rgba(34, 197, 94, 0.7)',
            'Fiber Break': 'rgba(239, 68, 68, 0.7)',
            'High Loss': 'rgba(245, 158, 11, 0.7)',
            'Splice Loss': 'rgba(59, 130, 246, 0.7)'
        };
        
        // Create chart
        faultDistributionChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: labels.map(label => backgroundColors[label] || 'rgba(156, 163, 175, 0.7)'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    function updateSignalPowerChart(measurements) {
        const ctx = document.getElementById('signalPowerChart').getContext('2d');
        
        // Destroy previous chart if it exists
        if (signalPowerChart) {
            signalPowerChart.destroy();
        }
        
        // Sort measurements by timestamp
        measurements.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Prepare data for chart
        const labels = measurements.map(m => {
            const date = new Date(m.timestamp);
            return date.toLocaleTimeString();
        });
        
        const signalPowerData = measurements.map(m => m.signal_power);
        
        // Create chart
        signalPowerChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Signal Power (dB)',
                    data: signalPowerData,
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'Signal Power (dB)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
    }
    
    function updateRecentMeasurements(measurements) {
        const tableBody = document.querySelector('#recentMeasurements tbody');
        
        if (measurements.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="empty-table">No measurements recorded yet.</td></tr>';
            return;
        }
        
        let html = '';
        
        measurements.forEach(m => {
            const timestamp = new Date(m.timestamp).toLocaleString();
            const faultClass = getFaultClass(m.fault_type);
            
            html += `
            <tr>
                <td>${timestamp}</td>
                <td>${m.device_name || 'Unknown'}</td>
                <td>${m.signal_power} dB</td>
                <td>${m.attenuation} dB/km</td>
                <td>${m.distance} m</td>
                <td class="${faultClass}">${m.fault_type}</td>
                <td>${(m.confidence * 100).toFixed(1)}%</td>
            </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function getFaultClass(faultType) {
        switch (faultType) {
            case 'No Fault': return 'text-success';
            case 'Fiber Break': return 'text-danger';
            case 'High Loss': return 'text-warning';
            case 'Splice Loss': return 'text-info';
            default: return '';
        }
    }
});