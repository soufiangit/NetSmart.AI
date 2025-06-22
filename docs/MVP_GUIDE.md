# SKMA-FON MVP Quick Start Guide

## Overview
This MVP demonstrates a complete Linux kernel-based monitoring system for optical fiber networks with AI-powered anomaly detection and real-time dashboard visualization.

## System Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kernel Module │────│  Python Agent   │────│  Cloud Dashboard│
│   (/proc/mmap)  │    │  (AI + REST)    │    │   (React-like)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features Implemented
- ✅ Linux kernel module with /proc interface
- ✅ Memory-mapped shared data between kernel and userspace
- ✅ Python monitoring agent with Flask API
- ✅ AI-based anomaly detection using Isolation Forest
- ✅ Traffic forecasting with linear regression
- ✅ Real-time web dashboard with charts
- ✅ SQLite database for metrics storage
- ✅ Docker containerization
- ✅ Automated deployment with Make

## Quick Deployment

### Prerequisites
- Docker 24.0+
- Docker Compose
- Make (optional but recommended)

### Deploy in 30 seconds
```bash
# Clone and enter directory
git clone <repo-url>
cd NetSmart.AI

# Deploy entire system
make deploy

# Or manually with docker-compose
docker-compose up -d
```

### Access the System
- **Dashboard**: http://localhost:3000
- **Cloud API**: http://localhost:5000  
- **Agent API**: http://localhost:8080

## Monitored Sites
The MVP simulates 4 optical fiber sites:
1. **MicrosoftDC** - Primary data center
2. **Dallas** - Regional hub
3. **Dobbins** - Distribution point
4. **Stone** - Edge location

## Key Metrics
- **Throughput**: 800-2000 Gbps per site
- **Utilization**: Real-time percentage
- **Error Counts**: BER and general errors
- **Anomaly Scores**: 0.0-1.0 (AI-generated)
- **Forecasts**: 15-minute ahead predictions

## Development Commands
```bash
# View all available commands
make help

# Check system status
make status

# View logs
make logs

# Run tests
make test

# Clean up
make clean
```

## API Endpoints

### Cloud API (Port 5000)
- `GET /api/health` - Health check
- `GET /api/metrics` - Latest metrics
- `GET /api/sites` - List monitored sites
- `GET /api/anomalies` - Anomalous metrics
- `GET /api/alerts` - Recent alerts
- `POST /api/metrics` - Ingest new metrics

### Agent API (Port 8080)
- `GET /health` - Agent health
- `GET /metrics` - Agent metrics
- `GET /anomalies` - Detected anomalies

## Troubleshooting

### Services won't start
```bash
# Check dependencies
make check-deps

# View detailed logs
docker-compose logs -f
```

### Dashboard shows no data
```bash
# Verify services are running
make status

# Check if agent is sending data
curl http://localhost:8080/health
curl http://localhost:5000/api/metrics
```

### Kernel module issues
```bash
# Build module locally (requires kernel headers)
make kernel

# Check if module loaded in container
docker exec skma-fon-agent lsmod | grep monitoring
```

## Scaling Considerations
For production deployment:
1. Replace SQLite with PostgreSQL/InfluxDB
2. Add Redis for caching
3. Implement proper authentication
4. Add Prometheus/Grafana monitoring
5. Use Kubernetes for orchestration
6. Add SSL/TLS termination

## Project Structure
```
NetSmart.AI/
├── kernel/                 # Linux kernel module
├── agent/                  # Python monitoring agent
├── ai/                     # AI inference engine
├── cloud/api/              # Cloud REST API
├── dashboard/              # Web dashboard
├── docker-compose.yml     # Container orchestration
├── Makefile               # Build automation
└── README.md              # This file
```

## Next Steps
1. **Enhanced AI Models**: Implement LSTM for better forecasting
2. **Real Hardware Integration**: Connect to actual optical equipment
3. **Advanced Analytics**: Add trend analysis and capacity planning
4. **Mobile App**: Create mobile dashboard
5. **Integration APIs**: Add webhook notifications
6. **Multi-tenant**: Support multiple organizations

## Support
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: See `/docs` directory
- **Email**: support@skma-fon.dev

## License
MIT License - see LICENSE file for details.

---
**Designed and Built by Soufian Carson**
*Smart Kernel-Based Monitoring Agent for Fiber-Optimized Optical Networks*