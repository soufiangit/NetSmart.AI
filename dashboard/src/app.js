// SKMA-FON Dashboard JavaScript
class SKMADashboard {
    constructor() {
        this.apiUrl = window.location.hostname === 'localhost' ? 
            'http://localhost:5000' : 
            `http://${window.location.hostname}:5000`;
        
        this.isConnected = false;
        this.charts = {};
        this.metricsHistory = [];
        this.refreshInterval = 5000; // 5 seconds
        
        this.init();
    }
    
    init() {
        console.log('Initializing SKMA-FON Dashboard...');
        this.setupElements();
        this.initCharts();
        this.startDataRefresh();
        this.updateConnectionStatus('connecting');
    }
    
    setupElements() {
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            statusText: document.getElementById('statusText'),
            totalSites: document.getElementById('totalSites'),
            activeAlerts: document.getElementById('activeAlerts'),
            totalThroughput: document.getElementById('totalThroughput'),
            avgUtilization: document.getElementById('avgUtilization'),
            sitesGrid: document.getElementById('sitesGrid'),
            alertsContainer: document.getElementById('alertsContainer'),
            lastUpdated: document.getElementById('lastUpdated')
        };
    }
    
    async fetchData(endpoint) {
        try {
            const response = await fetch(`${this.apiUrl}/api${endpoint}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            throw error;
        }
    }
    
    async loadDashboardData() {
        try {
            // Fetch latest metrics
            const metricsData = await this.fetchData('/metrics?limit=50');
            
            // Fetch alerts
            const alertsData = await this.fetchData('/alerts?hours=1');
            
            // Update dashboard
            this.updateOverviewStats(metricsData.metrics);
            this.updateSitesGrid(metricsData.metrics);
            this.updateCharts(metricsData.metrics);
            this.updateAlerts(alertsData.alerts);
            
            // Update connection status
            this.updateConnectionStatus('connected');
            this.elements.lastUpdated.textContent = new Date().toLocaleString();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.updateConnectionStatus('error');
        }
    }
    
    updateConnectionStatus(status) {
        const dot = this.elements.connectionStatus.querySelector('.dot');
        const statusText = this.elements.statusText;
        
        dot.className = 'dot';
        
        switch (status) {
            case 'connected':
                dot.classList.add('connected');
                statusText.textContent = 'Connected';
                this.isConnected = true;
                break;
            case 'error':
                dot.classList.add('error');
                statusText.textContent = 'Connection Error';
                this.isConnected = false;
                break;
            case 'connecting':
            default:
                statusText.textContent = 'Connecting...';
                this.isConnected = false;
                break;
        }
    }
    
    updateOverviewStats(metrics) {
        if (!metrics || metrics.length === 0) {
            return;
        }
        
        // Group metrics by site to get latest for each
        const siteMetrics = this.groupMetricsBySite(metrics);
        const sites = Object.keys(siteMetrics);
        
        // Calculate totals
        let totalThroughput = 0;
        let totalUtilization = 0;
        let alertCount = 0;
        
        sites.forEach(siteName => {
            const latest = siteMetrics[siteName][0]; // Most recent
            totalThroughput += latest.throughput_gbps || 0;
            totalUtilization += latest.utilization || 0;
            
            if (latest.anomaly_score >= 0.8 || latest.utilization >= 90) {
                alertCount++;
            }
        });
        
        const avgUtilization = sites.length > 0 ? totalUtilization / sites.length : 0;
        
        // Update UI
        this.elements.totalSites.textContent = sites.length;
        this.elements.activeAlerts.textContent = alertCount;
        this.elements.totalThroughput.textContent = `${totalThroughput.toLocaleString()} Gbps`;
        this.elements.avgUtilization.textContent = `${avgUtilization.toFixed(1)}%`;
        
        // Update alert styling
        this.elements.activeAlerts.className = alertCount > 0 ? 'stat-value alert' : 'stat-value';
    }
    
    groupMetricsBySite(metrics) {
        const grouped = {};
        metrics.forEach(metric => {
            if (!grouped[metric.site_name]) {
                grouped[metric.site_name] = [];
            }
            grouped[metric.site_name].push(metric);
        });
        
        // Sort each site's metrics by timestamp (newest first)
        Object.keys(grouped).forEach(site => {
            grouped[site].sort((a, b) => b.timestamp - a.timestamp);
        });
        
        return grouped;
    }
    
    updateSitesGrid(metrics) {
        const siteMetrics = this.groupMetricsBySite(metrics);
        const sitesArray = Object.keys(siteMetrics).map(siteName => ({
            name: siteName,
            metrics: siteMetrics[siteName][0] // Latest metrics
        }));
        
        if (sitesArray.length === 0) {
            this.elements.sitesGrid.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <span>No site data available</span>
                </div>
            `;
            return;
        }
        
        this.elements.sitesGrid.innerHTML = sitesArray.map(site => {
            const metric = site.metrics;
            const status = this.getSiteStatus(metric);
            const timestamp = new Date(metric.timestamp * 1000).toLocaleString();
            
            return `
                <div class="site-card ${status}">
                    <div class="site-name">${site.name}</div>
                    <div class="site-throughput">${metric.throughput_gbps} Gbps</div>
                    
                    <div class="site-metrics">
                        <div class="metric">
                            <span class="metric-label">Utilization:</span>
                            <span class="metric-value">${metric.utilization.toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Errors:</span>
                            <span class="metric-value">${metric.error_count}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">BER Errors:</span>
                            <span class="metric-value">${metric.ber_errors}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Link Status:</span>
                            <span class="metric-value">${metric.link_status ? 'UP' : 'DOWN'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Anomaly Score:</span>
                            <span class="metric-value">${metric.anomaly_score.toFixed(3)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Forecast:</span>
                            <span class="metric-value">${metric.forecast_gbps} Gbps</span>
                        </div>
                    </div>
                    
                    <div class="site-timestamp">Last updated: ${timestamp}</div>
                    
                    ${metric.anomaly_score >= 0.8 ? '<div class="alert-badge">ANOMALY DETECTED</div>' : ''}
                    ${metric.utilization >= 90 ? '<div class="alert-badge">HIGH UTILIZATION</div>' : ''}
                </div>
            `;
        }).join('');
    }
    
    getSiteStatus(metric) {
        if (metric.anomaly_score >= 0.8) return 'anomaly';
        if (metric.utilization >= 90) return 'warning';
        return 'normal';
    }
    
    initCharts() {
        // Throughput Chart
        const throughputCtx = document.getElementById('throughputChart').getContext('2d');
        this.charts.throughput = new Chart(throughputCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Throughput (Gbps)'
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
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        // Utilization Chart
        const utilizationCtx = document.getElementById('utilizationChart').getContext('2d');
        this.charts.utilization = new Chart(utilizationCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3498db',
                        '#27ae60',
                        '#f39c12',
                        '#e74c3c'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    updateCharts(metrics) {
        this.updateThroughputChart(metrics);
        this.updateUtilizationChart(metrics);
    }
    
    updateThroughputChart(metrics) {
        const siteMetrics = this.groupMetricsBySite(metrics);
        const sites = Object.keys(siteMetrics);
        
        // Get last 10 data points for each site
        const datasets = sites.map((siteName, index) => {
            const siteData = siteMetrics[siteName].slice(0, 10).reverse();
            const colors = ['#3498db', '#27ae60', '#f39c12', '#e74c3c'];
            
            return {
                label: siteName,
                data: siteData.map(m => m.throughput_gbps),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                tension: 0.1
            };
        });
        
        // Create time labels
        const labels = [];
        if (sites.length > 0) {
            const firstSite = siteMetrics[sites[0]].slice(0, 10).reverse();
            labels.push(...firstSite.map(m => 
                new Date(m.timestamp * 1000).toLocaleTimeString()
            ));
        }
        
        this.charts.throughput.data.labels = labels;
        this.charts.throughput.data.datasets = datasets;
        this.charts.throughput.update();
    }
    
    updateUtilizationChart(metrics) {
        const siteMetrics = this.groupMetricsBySite(metrics);
        const sites = Object.keys(siteMetrics);
        
        const labels = sites;
        const data = sites.map(siteName => {
            const latest = siteMetrics[siteName][0];
            return latest.utilization;
        });
        
        this.charts.utilization.data.labels = labels;
        this.charts.utilization.data.datasets[0].data = data;
        this.charts.utilization.update();
    }
    
    updateAlerts(alerts) {
        if (!alerts || alerts.length === 0) {
            this.elements.alertsContainer.innerHTML = `
                <div class="alert-item">
                    <div class="alert-content">
                        <div class="alert-message">No recent alerts</div>
                        <div class="alert-details">System is operating normally</div>
                    </div>
                </div>
            `;
            return;
        }
        
        this.elements.alertsContainer.innerHTML = alerts.map(alert => {
            const timestamp = new Date(alert.timestamp * 1000).toLocaleString();
            
            return `
                <div class="alert-item ${alert.severity}">
                    <div class="alert-content">
                        <div class="alert-message">${alert.message}</div>
                        <div class="alert-details">Site: ${alert.site} | Type: ${alert.type}</div>
                    </div>
                    <div class="alert-time">${timestamp}</div>
                </div>
            `;
        }).join('');
    }
    
    startDataRefresh() {
        // Initial load
        this.loadDashboardData();
        
        // Set up periodic refresh
        setInterval(() => {
            this.loadDashboardData();
        }, this.refreshInterval);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SKMADashboard();
});

// Add some utility functions for debugging
window.dashboardUtils = {
    toggleRefresh: () => {
        if (window.dashboard.refreshInterval) {
            clearInterval(window.dashboard.refreshInterval);
            window.dashboard.refreshInterval = null;
            console.log('Auto-refresh disabled');
        } else {
            window.dashboard.startDataRefresh();
            console.log('Auto-refresh enabled');
        }
    },
    
    manualRefresh: () => {
        console.log('Manual refresh triggered');
        window.dashboard.loadDashboardData();
    },
    
    getMetrics: async () => {
        return await window.dashboard.fetchData('/metrics');
    }
};