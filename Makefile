# SKMA-FON MVP Makefile
# Smart Kernel-Based Monitoring Agent for Fiber-Optimized Optical Networks
# Author: Soufian Carson

.PHONY: help build deploy clean test logs status kernel agent api dashboard install-deps check-deps

# Default target
all: help

# Help target
help:
	@echo "SKMA-FON MVP - Available Commands:"
	@echo "=================================="
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build          - Build all Docker images"
	@echo "  make deploy         - Deploy the complete system"
	@echo "  make start          - Start all services"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo ""
	@echo "Development:"
	@echo "  make kernel         - Build and test kernel module"
	@echo "  make agent          - Run Python agent locally"
	@echo "  make api            - Run cloud API locally"
	@echo "  make dashboard      - Serve dashboard locally"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status         - Show service status"
	@echo "  make logs           - Show service logs"
	@echo "  make test           - Run system tests"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean up containers and images"
	@echo "  make reset          - Reset entire system"
	@echo "  make install-deps   - Install development dependencies"
	@echo ""
	@echo "URLs after deployment:"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  Cloud API: http://localhost:5000"
	@echo "  Agent API: http://localhost:8080"

# Check if required tools are installed
check-deps:
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Please install Docker."; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Please install Docker Compose."; exit 1; }
	@echo "✓ All dependencies are available"

# Install development dependencies
install-deps:
	@echo "Installing development dependencies..."
	@if command -v brew >/dev/null 2>&1; then \
		brew install make; \
	elif command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y build-essential python3 python3-pip; \
	elif command -v yum >/dev/null 2>&1; then \
		sudo yum groupinstall -y "Development Tools" && sudo yum install -y python3 python3-pip; \
	else \
		echo "Please install build tools manually for your system"; \
	fi
	@echo "✓ Development dependencies installed"

# Build all Docker images
build: check-deps
	@echo "Building SKMA-FON Docker images..."
	docker-compose build --no-cache
	@echo "✓ All images built successfully"

# Deploy the complete system
deploy: check-deps build
	@echo "Deploying SKMA-FON system..."
	docker-compose up -d
	@echo ""
	@echo "✓ SKMA-FON MVP deployed successfully!"
	@echo ""
	@echo "Services:"
	@echo "  📊 Dashboard: http://localhost:3000"
	@echo "  🌐 Cloud API: http://localhost:5000"
	@echo "  🔧 Agent API: http://localhost:8080"
	@echo ""
	@echo "Useful commands:"
	@echo "  make status  - Check service status"
	@echo "  make logs    - View logs"
	@echo "  make test    - Run tests"

# Start services
start: check-deps
	@echo "Starting SKMA-FON services..."
	docker-compose up -d
	@echo "✓ Services started"

# Stop services
stop:
	@echo "Stopping SKMA-FON services..."
	docker-compose down
	@echo "✓ Services stopped"

# Restart services
restart: stop start

# Show service status
status:
	@echo "SKMA-FON Service Status:"
	@echo "========================"
	@docker-compose ps
	@echo ""
	@echo "Service Health Checks:"
	@echo "----------------------"
	@echo -n "Cloud API: "
	@curl -s http://localhost:5000/api/health >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Agent API: "
	@curl -s http://localhost:8080/health >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Dashboard: "
	@curl -s http://localhost:3000/health >/dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"

# Show logs
logs:
	@echo "SKMA-FON Service Logs (last 50 lines each):"
	@echo "============================================="
	@echo ""
	@echo "🌐 Cloud API Logs:"
	@echo "------------------"
	@docker-compose logs --tail=50 skma-api || true
	@echo ""
	@echo "🔧 Agent Logs:"
	@echo "--------------"
	@docker-compose logs --tail=50 skma-agent || true
	@echo ""
	@echo "📊 Dashboard Logs:"
	@echo "------------------"
	@docker-compose logs --tail=50 skma-dashboard || true

# Follow logs in real-time
logs-follow:
	docker-compose logs -f

# Run system tests
test: check-deps
	@echo "Running SKMA-FON system tests..."
	@echo ""
	@echo "Testing Cloud API..."
	@curl -s http://localhost:5000/api/health | grep -q "healthy" && echo "✓ Cloud API health check passed" || echo "✗ Cloud API health check failed"
	@curl -s http://localhost:5000/api/metrics | grep -q "timestamp" && echo "✓ Cloud API metrics endpoint working" || echo "✗ Cloud API metrics endpoint failed"
	@echo ""
	@echo "Testing Agent API..."
	@curl -s http://localhost:8080/health | grep -q "healthy" && echo "✓ Agent API health check passed" || echo "✗ Agent API health check failed"
	@echo ""
	@echo "Testing Grafana..."
	@curl -s http://localhost:3000/api/health | grep -q "ok" && echo "✓ Grafana health check passed" || echo "✗ Grafana health check failed"
	@curl -s -u admin:admin http://localhost:3000/api/datasources | grep -q "InfluxDB" && echo "✓ Grafana InfluxDB datasource found" || echo "✗ Grafana InfluxDB datasource not found"
	@curl -s -u admin:admin http://localhost:3000/api/search?query=SKMA-FON | grep -q "dashboard" && echo "✓ Grafana dashboard found" || echo "✗ Grafana dashboard not found"
	@echo ""
	@echo "Testing InfluxDB..."
	@curl -s -I http://localhost:8086/ping | grep -q "204 No Content" && echo "✓ InfluxDB health check passed" || echo "✗ InfluxDB health check failed"
	@echo ""
	@echo "Testing Web Dashboard..."
	@curl -s http://localhost:8000 | grep -q "SKMA-FON Dashboard" && echo "✓ Web dashboard available" || echo "✗ Web dashboard not available"
	@echo ""
	@echo "✓ System tests completed"

# Build and test kernel module locally
kernel:
	@echo "Building kernel module..."
	@cd kernel && make clean && make
	@echo "✓ Kernel module built"
	@echo ""
	@echo "To load the module (requires sudo):"
	@echo "  cd kernel && sudo ./load_module.sh load"

# Run Python agent locally (development mode)
agent:
	@echo "Installing agent dependencies..."
	@cd agent && pip install -r requirements.txt
	@echo "Starting Python agent in development mode..."
	@cd agent && PYTHONPATH=../ai/src python src/agent.py

# Run cloud API locally (development mode)
api:
	@echo "Installing API dependencies..."
	@cd cloud/api && pip install -r requirements.txt
	@echo "Starting Cloud API in development mode..."
	@cd cloud/api && python app.py

# Serve dashboard locally (development mode)
dashboard:
	@echo "Starting dashboard locally..."
	@echo "Dashboard available at: http://localhost:8000"
	@cd dashboard/src && python -m http.server 8000

# Clean up containers and images
clean:
	@echo "Cleaning up SKMA-FON containers and images..."
	docker-compose down --rmi all --volumes --remove-orphans
	@echo "✓ Cleanup completed"

# Reset entire system
reset: clean
	@echo "Resetting SKMA-FON system..."
	docker system prune -f
	@echo "✓ System reset completed"

# Development helpers
dev-setup: install-deps
	@echo "Setting up development environment..."
	@cd agent && pip install -r requirements.txt
	@cd cloud/api && pip install -r requirements.txt
	@echo "✓ Development environment ready"

# Quick deployment for demos
demo: build
	@echo "Starting SKMA-FON demo..."
	docker-compose up -d
	@sleep 10
	@echo ""
	@echo "🎉 SKMA-FON Demo is ready!"
	@echo ""
	@echo "Open these URLs:"
	@echo "  📊 Dashboard: http://localhost:3000"
	@echo "  🌐 API Docs:  http://localhost:5000"
	@echo ""
	@echo "The system is now monitoring 4 simulated optical fiber sites:"
	@echo "  • MicrosoftDC"
	@echo "  • Dallas"
	@echo "  • Dobbins" 
	@echo "  • Stone"
	@echo ""
	@echo "Features demonstrated:"
	@echo "  ✓ Real-time throughput monitoring"
	@echo "  ✓ AI-based anomaly detection"
	@echo "  ✓ Traffic forecasting"
	@echo "  ✓ Cloud dashboard with alerts"
	@echo ""
	@echo "To stop the demo: make stop"

# Check if system is ready
ready:
	@echo "Checking if SKMA-FON is ready..."
	@for i in {1..30}; do \
		if curl -s http://localhost:5000/api/health >/dev/null 2>&1 && \
		   curl -s http://localhost:8080/health >/dev/null 2>&1 && \
		   curl -s http://localhost:3000/health >/dev/null 2>&1; then \
			echo "✓ SKMA-FON is ready!"; \
			exit 0; \
		fi; \
		echo "Waiting for services... ($$i/30)"; \
		sleep 2; \
	done; \
	echo "✗ Services not ready after 60 seconds"; \
	exit 1