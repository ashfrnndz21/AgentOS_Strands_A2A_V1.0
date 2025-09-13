#!/bin/bash

echo "🚀 Starting All Backend Services..."
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is free
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is free
    fi
}

# Function to wait for service to start
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=10
    local attempt=1
    
    echo "   Waiting for $service_name to start on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if lsof -ti:$port >/dev/null 2>&1; then
            echo -e "   ${GREEN}✅ $service_name started successfully${NC}"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "   ${RED}❌ $service_name failed to start${NC}"
    return 1
}

# Function to test service health
test_service() {
    local url=$1
    local service_name=$2
    
    echo "   Testing $service_name health..."
    
    if curl -s "$url" >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ $service_name is responding${NC}"
        return 0
    else
        echo -e "   ${YELLOW}⚠️  $service_name not responding yet${NC}"
        return 1
    fi
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if Python virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}❌ Virtual environment not found at backend/venv${NC}"
    echo "   Please run: python3 -m venv backend/venv"
    exit 1
fi

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found${NC}"
    echo "   Please install Node.js from: https://nodejs.org"
    exit 1
else
    echo -e "${GREEN}✅ Node.js found ($(node --version))${NC}"
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found${NC}"
    echo "   Please install npm"
    exit 1
else
    echo -e "${GREEN}✅ npm found ($(npm --version))${NC}"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  node_modules not found${NC}"
    echo "   Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ node_modules found${NC}"
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama not found in PATH${NC}"
    echo "   Install from: https://ollama.ai"
else
    echo -e "${GREEN}✅ Ollama found${NC}"
fi

echo ""
echo "🧹 Cleaning up any existing services..."
./kill-all-services.sh >/dev/null 2>&1

echo ""
echo "🚀 Starting services..."

# Start Ollama core service (if not already running)
echo -e "${BLUE}1. Starting Ollama Core Service...${NC}"
if ! check_port 11434; then
    echo "   Ollama already running on port 11434"
else
    echo "   Starting Ollama serve..."
    ollama serve >/dev/null 2>&1 &
    wait_for_service 11434 "Ollama Core"
fi

# Start RAG API (Document Chat)
echo -e "${BLUE}2. Starting RAG API (Document Chat)...${NC}"
if ! check_port 5003; then
    echo -e "${RED}   Port 5003 is still in use!${NC}"
    exit 1
fi

echo "   Starting RAG API on port 5003..."
cd backend
source venv/bin/activate
python rag_api.py >/dev/null 2>&1 &
RAG_PID=$!
cd ..

wait_for_service 5003 "RAG API"
if [ $? -eq 0 ]; then
    # Test the service
    sleep 3
    test_service "http://localhost:5003/health" "RAG API"
fi

# Start Ollama API (Terminal & Agents)
echo -e "${BLUE}3. Starting Ollama API (Terminal & Agents)...${NC}"
if ! check_port 5002; then
    echo -e "${RED}   Port 5002 is still in use!${NC}"
    exit 1
fi

echo "   Starting Ollama API on port 5002..."
cd backend
source venv/bin/activate
python ollama_api.py >/dev/null 2>&1 &
OLLAMA_API_PID=$!
cd ..

wait_for_service 5002 "Ollama API"
if [ $? -eq 0 ]; then
    # Test the service
    sleep 3
    test_service "http://localhost:5002/health" "Ollama API"
fi

# Start Frontend (Vite)
echo -e "${BLUE}4. Starting Frontend (Vite)...${NC}"
if ! check_port 5173; then
    echo -e "${RED}   Port 5173 is still in use!${NC}"
    exit 1
fi

echo "   Starting Vite dev server on port 5173..."
npm run dev >/dev/null 2>&1 &
FRONTEND_PID=$!

wait_for_service 5173 "Frontend"
if [ $? -eq 0 ]; then
    # Test the service
    sleep 3
    test_service "http://localhost:5173" "Frontend"
fi

echo ""
echo "📊 Service Status Summary:"
echo "=========================="

# Check all services
services=(
    "11434:Ollama Core"
    "5002:Ollama API"
    "5003:RAG API"
    "5173:Frontend"
)

all_running=true

for service in "${services[@]}"; do
    port=$(echo $service | cut -d: -f1)
    name=$(echo $service | cut -d: -f2)
    
    if lsof -ti:$port >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $name (port $port) - Running${NC}"
    else
        echo -e "${RED}❌ $name (port $port) - Not Running${NC}"
        all_running=false
    fi
done

echo ""
if [ "$all_running" = true ]; then
    echo -e "${GREEN}🎉 All services started successfully!${NC}"
    echo ""
    echo "📡 Service URLs:"
    echo "   • Frontend: http://localhost:5173"
    echo "   • Ollama Core: http://localhost:11434"
    echo "   • Ollama API: http://localhost:5002"
    echo "   • RAG API: http://localhost:5003"
    echo ""
    echo "🌐 Application is ready!"
    echo "   • Open your browser: http://localhost:5173"
    echo ""
    echo "🛑 To stop all services, run: ./kill-all-services.sh"
else
    echo -e "${RED}❌ Some services failed to start${NC}"
    echo "   Check the logs and try again"
    exit 1
fi

echo "==================================="