# Welcome to AshRepo - AI Agent Platform

## Project info

**Repository**: AshRepo AI Agent Platform  
**Description**: Advanced multi-industry AI agent management platform

## How can I edit this code?

There are several ways of editing your application.

**Use your preferred IDE**

You can clone this repo and push changes directly.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone https://github.com/ashfrnndz21/AgentOS_StudioV2.git

# Step 2: Navigate to the project directory.
cd AgentOS_StudioV2

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Set up Python backend environment
python3 -m venv backend/venv
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate
pip install -r backend/requirements.txt

# Step 5: Install and start Ollama (for AI models)
# Download from https://ollama.ai and run:
ollama serve

# Step 6: Start the complete application (frontend + backend)
./manage-app.sh start
```

## 🚀 Quick Start with Automation Scripts

We've included powerful automation scripts for easy application management:

### **Master Control Script**
```bash
./manage-app.sh [command]
```

**Available Commands:**
- `start` - Start all services (frontend + backend)
- `stop` - Stop all services  
- `restart` - Restart all services
- `status` - Check status of all services
- `help` - Show help information

### **Individual Scripts**
```bash
# Start all services with health checks
./start-all-services.sh

# Stop all services cleanly
./kill-all-services.sh
```

### **Service Architecture**
The application runs multiple services:
- **Frontend (Vite)**: `http://localhost:5173` - React/TypeScript UI
- **Ollama API**: `http://localhost:5002` - AI model management & terminal
- **RAG API**: `http://localhost:5003` - Document chat with AI
- **Ollama Core**: `http://localhost:11434` - AI model service

### **Prerequisites**
- **Node.js & npm** - [Install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)
- **Python 3.8+** - For backend services
- **Ollama** - [Download from ollama.ai](https://ollama.ai)

### **Manual Setup (Alternative)**
If you prefer manual setup:

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

This project can be deployed using various methods:

- **Vercel**: Connect your GitHub repository to Vercel for automatic deployments
- **Netlify**: Deploy directly from your Git repository
- **Docker**: Use the included Docker configurations for containerized deployment
- **Traditional hosting**: Build the project and serve the static files

## 🎯 Features

### **AI & Document Processing**
- **Ollama Integration**: Local AI model management and execution
- **Document Chat**: Upload and chat with documents using RAG (Retrieval Augmented Generation)
- **AI Terminal**: Interactive terminal for Ollama commands
- **Model Management**: Pull, delete, and manage AI models

### **Agent Management**
- **Multi-Agent Support**: Create and manage multiple AI agents
- **Agent Execution**: Run agents with custom prompts and configurations
- **Performance Metrics**: Track agent performance and usage statistics
- **Agent Persistence**: SQLite database for agent storage

### **Platform Features**
- **Multi-Industry Support**: Banking, Telco, Healthcare agent platforms
- **Real-time Monitoring**: Live agent performance tracking
- **Customizable Branding**: Logo and theme customization
- **Advanced Workflows**: Multi-agent orchestration capabilities
- **Backend Integration**: Full API integration with monitoring

### **Developer Experience**
- **Automated Service Management**: One-command startup/shutdown
- **Health Monitoring**: Automatic service health checks
- **Port Conflict Prevention**: Smart port management
- **Error Recovery**: Robust error handling and recovery
- **Development Tools**: Hot reload, debugging, and logging

## 🛠️ Troubleshooting

### **Common Issues**

**Port conflicts:**
```bash
# Clean all services and restart
./manage-app.sh restart
```

**Services not starting:**
```bash
# Check service status
./manage-app.sh status

# View detailed logs
./manage-app.sh logs
```

**Ollama not found:**
```bash
# Install Ollama from https://ollama.ai
# Then start it:
ollama serve
```

**Python dependencies:**
```bash
# Reinstall Python dependencies
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

### **Service URLs**
- **Application**: http://localhost:5173
- **Ollama API**: http://localhost:5002/health
- **RAG API**: http://localhost:5003/health
- **Ollama Core**: http://localhost:11434/api/tags

## 📋 Automation Scripts Documentation

### **manage-app.sh** - Master Control
The main application management script with comprehensive service control:

```bash
# Start everything
./manage-app.sh start

# Stop everything  
./manage-app.sh stop

# Restart all services
./manage-app.sh restart

# Check what's running
./manage-app.sh status

# Show help
./manage-app.sh help
```

### **start-all-services.sh** - Intelligent Startup
Comprehensive startup script with:
- ✅ Dependency verification (Node.js, Python, Ollama)
- ✅ Port conflict prevention
- ✅ Service health checks
- ✅ Proper startup sequencing
- ✅ Error handling and recovery

### **kill-all-services.sh** - Clean Shutdown
Robust service termination:
- ✅ Kills processes by port (most reliable)
- ✅ Kills processes by name pattern (backup)
- ✅ Verifies all ports are freed
- ✅ Handles stuck processes

### **Service Management Best Practices**
1. **Always use the automation scripts** - They handle edge cases and conflicts
2. **Check status before starting** - `./manage-app.sh status`
3. **Use restart for updates** - `./manage-app.sh restart`
4. **Monitor logs for issues** - `./manage-app.sh logs`

## 🔧 Development Workflow

### **Daily Development**
```bash
# Start your development session
./manage-app.sh start

# Check everything is running
./manage-app.sh status

# Make your changes...

# Restart if needed
./manage-app.sh restart

# End your session
./manage-app.sh stop
```

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Use the automation scripts for testing
4. Submit a pull request

## 📚 Architecture

### **Frontend (React/TypeScript)**
- **Framework**: Vite + React + TypeScript
- **UI**: shadcn-ui + Tailwind CSS
- **State Management**: React hooks and context
- **API Client**: Custom API client with error handling

### **Backend Services**
- **Ollama API** (`backend/ollama_api.py`): Flask-based API for AI model management
- **RAG API** (`backend/rag_api.py`): FastAPI-based document processing
- **Database**: SQLite for agent and document storage

### **AI Integration**
- **Ollama**: Local AI model execution
- **LangChain**: Document processing and RAG
- **ChromaDB**: Vector database for document embeddings
