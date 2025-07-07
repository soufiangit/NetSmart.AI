# NetSmart.AI

**Designed by Soufian Carson**

## Project Overview

A lightweight Linux-kernel monitoring agent that captures WaveServer AI CMD traffic and fiber-link health, shares it with user space through /proc + mmap, enriches it with AI-based anomaly detection and traffic forecasting, and streams the results to a cloud dashboard for real-time observability and auto-remediation.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kernel Module │────│  Python Agent   │────│  Cloud Dashboard│
│   (/proc/mmap)  │    │  (AI + REST)    │    │   (React UI)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites
- Ubuntu 22.04 LTS
- Docker 24.0+
- Linux kernel headers
- Python 3.12+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/scarson/NetSmart.AI.git
cd NetSmart.AI
```

2. Build and deploy:
```bash
make deploy
```

3. Access the dashboard:
```
http://localhost:3000
```

## Project Structure

```
NetSmart.AI/
├── kernel/                 # Linux kernel module
│   ├── monitoring_module.c
│   ├── Makefile
│   └── load_module.sh
├── agent/                  # Python user-space agent
│   ├── src/
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/              # React web dashboard
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── cloud/                  # Cloud infrastructure
│   ├── api/
│   ├── terraform/
│   └── docker-compose.yml
├── ai/                     # AI models and inference
│   ├── models/
│   └── inference.py
└── docs/                   # Documentation
```

## Features

- [x] Kernel module with /proc interface
- [x] Memory-mapped user space access
- [x] Python monitoring agent
- [x] AI anomaly detection
- [x] Cloud time-series database
- [x] Real-time web dashboard
- [x] Auto-remediation webhooks
- [x] Docker containerization



## License

MIT License - see LICENSE file for details.

