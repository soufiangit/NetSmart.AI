// SKMA-FON Grafana Integration
class SKMAGrafanaIntegration {
    constructor() {
        this.apiUrl = window.location.hostname === 'localhost' ? 
            'http://localhost:5000' : 
            `http://${window.location.hostname}:5000`;
        
        this.grafanaUrl = window.location.hostname === 'localhost' ? 
            'http://localhost:3000' : 
            `http://${window.location.hostname}:3000`;
        
        this.isConnected = false;
        this.refreshInterval = 5000; // 5 seconds
        
        this.init();
    }
    
    init() {
        console.log('Initializing SKMA-FON Grafana Integration...');
        this.setupElements();
        this.loadGrafanaDashboards();
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
            lastUpdated: document.getElementById('lastUpdated'),
            grafanaContainer: document.getElementById('grafanaDashboard')
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
    
    loadGrafanaDashboards() {
        // Load Grafana in iframe if grafanaContainer exists
        if (this.elements.grafanaContainer) {
            // Set default dashboard with auto-refresh
            const dashboardUrl = `${this.grafanaUrl}/d/skma-fon-dashboard/skma-fon-network-monitoring?orgId=1&refresh=5s&kiosk`;
            
            this.elements.grafanaContainer.innerHTML = `
                <iframe 
                    src="${dashboardUrl}" 
                    width="100%" 
                    height="100%" 
                    frameborder="0"
                    allow="fullscreen">
                </iframe>
            `;
            
            console.log('Grafana dashboard loaded:', dashboardUrl);
        } else {
            console.error('Grafana container not found in DOM');
        }
    }
    
    async loadSummaryData() {
        try {
            // Fetch latest metrics for summary stats only (not for visualization)
            const metricsData = await this.fetchData('/metrics?limit=20');
            
            // Fetch alerts
            const alertsData = await this.fetchData('/alerts?hours=1');
            
            // Update summary stats
            this.updateOverviewStats(metricsData.metrics);
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
        // Initial load of summary data
        this.loadSummaryData();
        
        // Set up periodic refresh of summary data
        setInterval(() => {
            this.loadSummaryData();
        }, this.refreshInterval);
    }
}

// Initialize Grafana integration when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SKMAGrafanaIntegration();
});

// Add some utility functions for debugging
window.dashboardUtils = {
    toggleRefresh: () => {
        const iframe = document.querySelector('#grafanaDashboard iframe');
        if (iframe) {
            const src = iframe.src;
            if (src.includes('refresh=5s')) {
                iframe.src = src.replace('refresh=5s', 'refresh=off');
                console.log('Auto-refresh disabled');
            } else {
                iframe.src = src.replace('refresh=off', 'refresh=5s');
                console.log('Auto-refresh enabled');
            }
        }
        
        if (window.dashboard.refreshInterval) {
            clearInterval(window.dashboard.refreshInterval);
            window.dashboard.refreshInterval = null;
            console.log('Summary data refresh disabled');
        } else {
            window.dashboard.startDataRefresh();
            console.log('Summary data refresh enabled');
        }
    },
    
    manualRefresh: () => {
        console.log('Manual refresh triggered');
        window.dashboard.loadSummaryData();
        
        const iframe = document.querySelector('#grafanaDashboard iframe');
        if (iframe) {
            iframe.src = iframe.src;
        }
    },
    
    getMetrics: async () => {
        return await window.dashboard.fetchData('/metrics');
    }
};