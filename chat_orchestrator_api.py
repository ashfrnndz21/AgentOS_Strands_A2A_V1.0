#!/usr/bin/env python3
"""
Strands Chat Orchestrator API
============================

A dedicated backend for intelligent chat routing and agent orchestration.
Supports Direct LLM, Independent Agents, and Agent Palette integration.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import sqlite3
import threading
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
STRANDS_API_URL = "http://localhost:5004"
DATABASE_PATH = "chat_orchestrator.db"

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ChatMessage:
    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ChatSession:
    id: str
    chat_type: str  # 'direct-llm', 'independent-agent', 'palette-agent'
    config: Dict[str, Any]
    created_at: datetime
    last_activity: datetime
    status: str = 'active'

@dataclass
class AgentRoute:
    agent_id: str
    confidence: float
    reasoning: str
    tools_needed: List[str] = None

# ============================================================================
# Database Setup
# ============================================================================

def init_database():
    """Initialize SQLite database for chat sessions and messages"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Chat sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            chat_type TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
    ''')
    
    # Agent routing history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_routes (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            agent_id TEXT,
            confidence REAL,
            reasoning TEXT,
            tools_used TEXT,
            execution_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized successfully")

# ============================================================================
# Ollama Integration
# ============================================================================

class OllamaClient:
    """Direct integration with Ollama for LLM operations"""
    
    @staticmethod
    def get_models():
        """Get available Ollama models"""
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=30)
            if response.status_code == 200:
                data = response.json()
                return [{"name": model["name"], "size": model["size"]} for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            return []
    
    @staticmethod
    def generate_response(model: str, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 1000):
        """Generate response using Ollama"""
        try:
            # Convert messages to Ollama format
            prompt = ""
            for msg in messages:
                if msg["role"] == "system":
                    prompt += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    prompt += f"Human: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    prompt += f"Assistant: {msg['content']}\n"
            
            prompt += "Assistant: "
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return {
                    "content": data.get("response", ""),
                    "model": model,
                    "tokens_used": data.get("eval_count", 0),
                    "generation_time": data.get("total_duration", 0) / 1000000000  # Convert to seconds
                }
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Failed to generate Ollama response: {e}")
            return None

# ============================================================================
# Agent Routing Intelligence
# ============================================================================

class AgentRouter:
    """Intelligent routing system for determining which agent should handle a query"""
    
    def __init__(self):
        self.routing_model = "qwen2.5:latest"  # Use a fast model for routing decisions
    
    def analyze_query(self, query: str, available_agents: List[Dict]) -> AgentRoute:
        """Analyze user query and determine best agent to handle it"""
        
        # Create routing prompt
        agent_descriptions = []
        for agent in available_agents:
            agent_descriptions.append(f"- {agent['name']}: {agent.get('description', '')} (Role: {agent.get('role', 'General')})")
        
        routing_prompt = f"""
You are an intelligent agent router. Analyze the user query and determine which agent is best suited to handle it.

Available Agents:
{chr(10).join(agent_descriptions)}

User Query: "{query}"

Respond with JSON in this exact format:
{{
    "agent_id": "best_agent_id_or_null",
    "confidence": 0.85,
    "reasoning": "Why this agent was chosen",
    "tools_needed": ["tool1", "tool2"]
}}

If no specific agent is needed, set agent_id to null and confidence to 0.3 or lower.
"""
        
        try:
            # Use Ollama to make routing decision
            response = OllamaClient.generate_response(
                model=self.routing_model,
                messages=[{"role": "user", "content": routing_prompt}],
                temperature=0.1,  # Low temperature for consistent routing
                max_tokens=200
            )
            
            if response and response["content"]:
                # Parse JSON response
                try:
                    routing_data = json.loads(response["content"].strip())
                    return AgentRoute(
                        agent_id=routing_data.get("agent_id"),
                        confidence=routing_data.get("confidence", 0.5),
                        reasoning=routing_data.get("reasoning", "Automatic routing"),
                        tools_needed=routing_data.get("tools_needed", [])
                    )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse routing response as JSON")
            
        except Exception as e:
            logger.error(f"Agent routing failed: {e}")
        
        # Fallback: no specific routing
        return AgentRoute(
            agent_id=None,
            confidence=0.2,
            reasoning="Fallback routing - no specific agent determined",
            tools_needed=[]
        )

# ============================================================================
# Chat Orchestrator
# ============================================================================

class ChatOrchestrator:
    """Main orchestrator for handling different chat types"""
    
    def __init__(self):
        self.agent_router = AgentRouter()
        self.ollama_client = OllamaClient()
    
    def create_session(self, chat_config: Dict) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_sessions (id, chat_type, config)
            VALUES (?, ?, ?)
        ''', (session_id, chat_config["type"], json.dumps(chat_config)))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created chat session: {session_id} (type: {chat_config['type']})")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by ID"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ChatSession(
                id=row[0],
                chat_type=row[1],
                config=json.loads(row[2]),
                created_at=datetime.fromisoformat(row[3]),
                last_activity=datetime.fromisoformat(row[4]),
                status=row[5]
            )
        return None
    
    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process user message and generate appropriate response"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Store user message
        message_id = str(uuid.uuid4())
        self._store_message(session_id, message_id, "user", user_message)
        
        # Process based on chat type
        if session.chat_type == "direct-llm":
            return self._handle_direct_llm(session, user_message, message_id)
        elif session.chat_type == "independent-agent":
            return self._handle_independent_agent(session, user_message, message_id)
        elif session.chat_type == "palette-agent":
            return self._handle_palette_agent(session, user_message, message_id)
        else:
            return {"error": f"Unknown chat type: {session.chat_type}"}
    
    def _handle_direct_llm(self, session: ChatSession, user_message: str, message_id: str) -> Dict[str, Any]:
        """Handle Direct LLM chat with intelligent routing"""
        config = session.config
        
        # Get conversation history
        messages = self._get_conversation_history(session.id)
        
        # Add system prompt if configured
        if config.get("systemPrompt"):
            messages.insert(0, {"role": "system", "content": config["systemPrompt"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Check if we should route to an agent
        available_agents = self._get_available_agents()
        if available_agents:
            routing = self.agent_router.analyze_query(user_message, available_agents)
            
            # If high confidence routing to specific agent
            if routing.agent_id and routing.confidence > 0.7:
                logger.info(f"🎯 Routing to agent {routing.agent_id} (confidence: {routing.confidence})")
                return self._execute_agent_routing(session, routing, user_message, message_id)
        
        # Generate direct LLM response
        response = self.ollama_client.generate_response(
            model=config.get("model", "qwen2.5:latest"),
            messages=messages,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("maxTokens", 1000)
        )
        
        if response:
            # Store assistant response
            assistant_message_id = str(uuid.uuid4())
            self._store_message(session.id, assistant_message_id, "assistant", response["content"])
            
            return {
                "message_id": assistant_message_id,
                "content": response["content"],
                "type": "direct-llm",
                "model": response["model"],
                "tokens_used": response["tokens_used"],
                "generation_time": response["generation_time"]
            }
        else:
            return {"error": "Failed to generate response"}
    
    def _handle_independent_agent(self, session: ChatSession, user_message: str, message_id: str) -> Dict[str, Any]:
        """Handle Independent Chat Agent"""
        config = session.config
        
        # Build agent persona prompt
        agent_prompt = f"""You are {config.get('name', 'Assistant')}, a {config.get('role', 'helpful assistant')}.

Personality: {config.get('personality', 'Professional and helpful')}
Capabilities: {', '.join(config.get('capabilities', []))}

{config.get('systemPrompt', 'You are a helpful AI assistant.')}
"""
        
        # Get conversation history
        messages = self._get_conversation_history(session.id)
        messages.insert(0, {"role": "system", "content": agent_prompt})
        messages.append({"role": "user", "content": user_message})
        
        # Generate response with agent persona
        response = self.ollama_client.generate_response(
            model=config.get("model", "qwen2.5:latest"),
            messages=messages,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("maxTokens", 1000)
        )
        
        if response:
            assistant_message_id = str(uuid.uuid4())
            self._store_message(session.id, assistant_message_id, "assistant", response["content"])
            
            return {
                "message_id": assistant_message_id,
                "content": response["content"],
                "type": "independent-agent",
                "agent_name": config.get('name'),
                "model": response["model"],
                "tokens_used": response["tokens_used"],
                "generation_time": response["generation_time"]
            }
        else:
            return {"error": "Failed to generate agent response"}
    
    def _handle_palette_agent(self, session: ChatSession, user_message: str, message_id: str) -> Dict[str, Any]:
        """Handle Palette Agent chat"""
        config = session.config
        agent_id = config.get("agentId")
        
        if not agent_id:
            return {"error": "No agent ID specified for palette agent chat"}
        
        # Get agent details from Strands API
        agent_details = self._get_agent_details(agent_id)
        if not agent_details:
            return {"error": f"Agent {agent_id} not found"}
        
        # Execute agent through Strands API
        try:
            strands_response = requests.post(f"{STRANDS_API_URL}/api/strands/agents/{agent_id}/execute", 
                json={"input": user_message})
            
            if strands_response.status_code == 200:
                result = strands_response.json()
                
                assistant_message_id = str(uuid.uuid4())
                self._store_message(session.id, assistant_message_id, "assistant", result.get("output", ""))
                
                return {
                    "message_id": assistant_message_id,
                    "content": result.get("output", ""),
                    "type": "palette-agent",
                    "agent_id": agent_id,
                    "agent_name": agent_details.get("name"),
                    "execution_time": result.get("execution_time", 0),
                    "tools_used": result.get("tools_used", [])
                }
            else:
                return {"error": f"Agent execution failed: {strands_response.status_code}"}
                
        except Exception as e:
            logger.error(f"Palette agent execution failed: {e}")
            return {"error": f"Agent execution error: {str(e)}"}
    
    def _execute_agent_routing(self, session: ChatSession, routing: AgentRoute, user_message: str, message_id: str) -> Dict[str, Any]:
        """Execute routed agent call"""
        # Store routing decision
        self._store_routing(session.id, message_id, routing)
        
        # Execute the routed agent
        try:
            strands_response = requests.post(f"{STRANDS_API_URL}/api/strands/agents/{routing.agent_id}/execute", 
                json={"input": user_message})
            
            if strands_response.status_code == 200:
                result = strands_response.json()
                
                assistant_message_id = str(uuid.uuid4())
                self._store_message(session.id, assistant_message_id, "assistant", result.get("output", ""))
                
                return {
                    "message_id": assistant_message_id,
                    "content": result.get("output", ""),
                    "type": "routed-agent",
                    "agent_id": routing.agent_id,
                    "routing_confidence": routing.confidence,
                    "routing_reasoning": routing.reasoning,
                    "execution_time": result.get("execution_time", 0),
                    "tools_used": result.get("tools_used", [])
                }
            else:
                # Fallback to direct LLM if agent fails
                return self._fallback_to_llm(session, user_message, message_id)
                
        except Exception as e:
            logger.error(f"Routed agent execution failed: {e}")
            return self._fallback_to_llm(session, user_message, message_id)
    
    def _fallback_to_llm(self, session: ChatSession, user_message: str, message_id: str) -> Dict[str, Any]:
        """Fallback to direct LLM when agent routing fails"""
        messages = self._get_conversation_history(session.id)
        messages.append({"role": "user", "content": user_message})
        
        response = self.ollama_client.generate_response(
            model=session.config.get("model", "qwen2.5:latest"),
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        if response:
            assistant_message_id = str(uuid.uuid4())
            self._store_message(session.id, assistant_message_id, "assistant", response["content"])
            
            return {
                "message_id": assistant_message_id,
                "content": response["content"],
                "type": "fallback-llm",
                "model": response["model"],
                "tokens_used": response["tokens_used"],
                "generation_time": response["generation_time"]
            }
        else:
            return {"error": "All response methods failed"}
    
    def _get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content FROM chat_messages 
            WHERE session_id = ? AND role != 'system'
            ORDER BY timestamp DESC LIMIT ?
        ''', (session_id, limit * 2))  # *2 to account for user/assistant pairs
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order
        messages = []
        for role, content in reversed(rows):
            messages.append({"role": role, "content": content})
        
        return messages
    
    def _get_available_agents(self) -> List[Dict]:
        """Get available agents from Strands API"""
        try:
            response = requests.get(f"{STRANDS_API_URL}/api/strands/agents")
            if response.status_code == 200:
                return response.json().get("agents", [])
        except Exception as e:
            logger.error(f"Failed to get available agents: {e}")
        return []
    
    def _get_agent_details(self, agent_id: str) -> Optional[Dict]:
        """Get specific agent details"""
        try:
            response = requests.get(f"{STRANDS_API_URL}/api/strands/agents/{agent_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get agent details: {e}")
        return None
    
    def _store_message(self, session_id: str, message_id: str, role: str, content: str, metadata: Dict = None):
        """Store message in database"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_messages (id, session_id, role, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, session_id, role, content, json.dumps(metadata) if metadata else None))
        
        # Update session last activity
        cursor.execute('''
            UPDATE chat_sessions SET last_activity = CURRENT_TIMESTAMP WHERE id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
    
    def _store_routing(self, session_id: str, message_id: str, routing: AgentRoute):
        """Store agent routing decision"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO agent_routes (id, session_id, message_id, agent_id, confidence, reasoning, tools_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), session_id, message_id, routing.agent_id, 
              routing.confidence, routing.reasoning, json.dumps(routing.tools_needed)))
        
        conn.commit()
        conn.close()

# ============================================================================
# API Endpoints
# ============================================================================

# Initialize orchestrator
orchestrator = ChatOrchestrator()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Chat Orchestrator API",
        "timestamp": datetime.now().isoformat(),
        "ollama_connected": len(OllamaClient.get_models()) > 0
    })

@app.route('/api/chat/models', methods=['GET'])
def get_models():
    """Get available Ollama models"""
    models = OllamaClient.get_models()
    return jsonify({"models": models})

@app.route('/api/chat/agents', methods=['GET'])
def get_agents():
    """Get available agents from palette"""
    agents = orchestrator._get_available_agents()
    return jsonify({"agents": agents})

@app.route('/api/chat/sessions', methods=['POST'])
def create_chat_session():
    """Create new chat session"""
    try:
        config = request.json
        if not config or not config.get("type"):
            return jsonify({"error": "Chat configuration required"}), 400
        
        session_id = orchestrator.create_session(config)
        return jsonify({
            "session_id": session_id,
            "status": "created",
            "chat_type": config["type"]
        })
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/sessions/<session_id>/messages', methods=['POST'])
def send_message(session_id):
    """Send message to chat session"""
    try:
        data = request.json
        if not data or not data.get("message"):
            return jsonify({"error": "Message content required"}), 400
        
        result = orchestrator.process_message(session_id, data["message"])
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/sessions/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat session history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = orchestrator._get_conversation_history(session_id, limit)
        
        return jsonify({
            "session_id": session_id,
            "messages": messages
        })
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/sessions/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """Get chat session information"""
    try:
        session = orchestrator.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({
            "session_id": session.id,
            "chat_type": session.chat_type,
            "config": session.config,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "status": session.status
        })
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/sessions', methods=['GET'])
def list_sessions():
    """List all chat sessions"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, chat_type, created_at, last_activity, status 
            FROM chat_sessions 
            ORDER BY last_activity DESC
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "chat_type": row[1],
                "created_at": row[2],
                "last_activity": row[3],
                "status": row[4]
            })
        
        conn.close()
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# Startup
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting Strands Chat Orchestrator API...")
    print("=" * 50)
    print("🎯 Features:")
    print("   • Direct LLM Chat with intelligent routing")
    print("   • Independent Chat Agents with personas")
    print("   • Agent Palette integration")
    print("   • Conversation history and context")
    print("   • Intelligent agent routing")
    print("   • Tool integration support")
    print("")
    print("🔗 Endpoints:")
    print("   • Health: http://localhost:5005/health")
    print("   • Models: http://localhost:5005/api/chat/models")
    print("   • Agents: http://localhost:5005/api/chat/agents")
    print("   • Sessions: http://localhost:5005/api/chat/sessions")
    print("")
    print("🔧 Dependencies:")
    print("   • Ollama: http://localhost:11434")
    print("   • Strands API: http://localhost:5004")
    print("")
    
    # Initialize database
    init_database()
    
    print("✅ Chat Orchestrator API ready!")
    print("🌐 Server starting on port 5005...")
    
    app.run(host='0.0.0.0', port=5005, debug=True)