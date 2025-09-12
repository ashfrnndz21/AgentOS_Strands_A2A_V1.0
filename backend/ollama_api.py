"""
Simple Ollama API Backend
Provides basic endpoints for Ollama agent management
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import sqlite3
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
DATABASE_PATH = "ollama_agents.db"

def init_database():
    """Initialize SQLite database for agent storage"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Agents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            description TEXT,
            model TEXT NOT NULL,
            personality TEXT,
            expertise TEXT,
            system_prompt TEXT,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 1000,
            guardrails_enabled BOOLEAN DEFAULT FALSE,
            safety_level TEXT DEFAULT 'medium',
            content_filters TEXT,
            custom_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents (id)
        )
    ''')
    
    # Executions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            input_text TEXT NOT NULL,
            output_text TEXT,
            success BOOLEAN DEFAULT FALSE,
            duration INTEGER,
            tokens_used INTEGER,
            error_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

@app.route('/api/ollama/status', methods=['GET'])
def get_ollama_status():
    """Check Ollama service status"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "status": "running",
                "models": data.get("models", []),
                "model_count": len(data.get("models", []))
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Ollama responded with status {response.status_code}"
            }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "not_running",
            "message": "Cannot connect to Ollama. Make sure Ollama is installed and running."
        }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/ollama/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return jsonify(data.get("models", []))
        else:
            return jsonify([]), 500
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return jsonify([]), 500

@app.route('/api/agents/ollama', methods=['POST'])
def create_agent():
    """Create a new Ollama agent"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('name') or not data.get('model'):
            return jsonify({"error": "Name and model are required"}), 400
        
        # Generate agent ID
        agent_id = str(uuid.uuid4())
        
        # Store in database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO agents (
                id, name, role, description, model, personality, expertise,
                system_prompt, temperature, max_tokens, guardrails_enabled,
                safety_level, content_filters, custom_rules
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            data.get('name'),
            data.get('role', ''),
            data.get('description', ''),
            data.get('model'),
            data.get('personality', ''),
            data.get('expertise', ''),
            data.get('systemPrompt', ''),
            data.get('temperature', 0.7),
            data.get('maxTokens', 1000),
            data.get('guardrails', {}).get('enabled', False),
            data.get('guardrails', {}).get('safetyLevel', 'medium'),
            json.dumps(data.get('guardrails', {}).get('contentFilters', [])),
            json.dumps(data.get('guardrails', {}).get('rules', []))
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "agent": {
                "id": agent_id,
                "name": data.get('name'),
                "role": data.get('role', ''),
                "description": data.get('description', ''),
                "model": {"model_id": data.get('model')},
                "system_prompt": data.get('systemPrompt', ''),
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('maxTokens', 1000),
                "guardrails": data.get('guardrails', {}),
                "capabilities": data.get('capabilities', {}),
                "behavior": data.get('behavior', {})
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/ollama', methods=['GET'])
def list_agents():
    """List all Ollama agents"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM agents ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        agents = []
        for row in rows:
            agent = {
                "id": row[0],
                "name": row[1],
                "role": row[2],
                "description": row[3],
                "model": {"model_id": row[4]},
                "personality": row[5],
                "expertise": row[6],
                "system_prompt": row[7],
                "temperature": row[8],
                "max_tokens": row[9],
                "guardrails": {
                    "enabled": bool(row[10]),
                    "safetyLevel": row[11],
                    "contentFilters": json.loads(row[12]) if row[12] else [],
                    "rules": json.loads(row[13]) if row[13] else []
                },
                "created_at": row[14],
                "updated_at": row[15]
            }
            agents.append(agent)
        
        conn.close()
        
        return jsonify({"agents": agents})
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return jsonify({"agents": []}), 500

@app.route('/api/agents/ollama/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """Delete an Ollama agent"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Delete agent
        cursor.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
        
        # Delete related conversations and executions
        cursor.execute('DELETE FROM conversations WHERE agent_id = ?', (agent_id,))
        cursor.execute('DELETE FROM executions WHERE agent_id = ?', (agent_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ollama/generate', methods=['POST'])
def generate_response():
    """Generate response using Ollama"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('model') or not data.get('prompt'):
            return jsonify({"error": "Model and prompt are required"}), 400
        
        # Prepare Ollama request
        ollama_request = {
            "model": data.get('model'),
            "prompt": data.get('prompt'),
            "stream": False,
            "options": {
                "temperature": data.get('temperature', 0.7),
                "num_predict": data.get('max_tokens', 1000)
            }
        }
        
        if data.get('system'):
            ollama_request['system'] = data.get('system')
        
        # Make request to Ollama
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=ollama_request,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "status": "success",
                "response": result.get("response", ""),
                "eval_count": result.get("eval_count", 0),
                "eval_duration": result.get("eval_duration", 0),
                "total_duration": result.get("total_duration", 0)
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Ollama API error: {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Request timed out"
        }), 408
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/agents/ollama/<agent_id>/execute', methods=['POST'])
def execute_agent(agent_id):
    """Execute an agent with input"""
    try:
        data = request.json
        input_text = data.get('input', '')
        
        if not input_text:
            return jsonify({"error": "Input is required"}), 400
        
        # Get agent from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        agent_row = cursor.fetchone()
        
        if not agent_row:
            conn.close()
            return jsonify({"error": "Agent not found"}), 404
        
        # Prepare execution
        start_time = datetime.now()
        execution_id = str(uuid.uuid4())
        
        try:
            # Build prompt
            system_prompt = agent_row[7]  # system_prompt column
            model = agent_row[4]  # model column
            temperature = agent_row[8]  # temperature column
            max_tokens = agent_row[9]  # max_tokens column
            
            prompt = f"System: {system_prompt}\n\nHuman: {input_text}\n\nAssistant:"
            
            # Generate response
            ollama_request = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=ollama_request,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                output_text = result.get("response", "")
                tokens_used = result.get("eval_count", 0)
                duration = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Store execution
                cursor.execute('''
                    INSERT INTO executions (
                        id, agent_id, input_text, output_text, success,
                        duration, tokens_used, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution_id, agent_id, input_text, output_text, True,
                    duration, tokens_used, datetime.now()
                ))
                
                conn.commit()
                conn.close()
                
                return jsonify({
                    "id": execution_id,
                    "agentId": agent_id,
                    "input": input_text,
                    "output": output_text,
                    "success": True,
                    "duration": duration,
                    "tokensUsed": tokens_used,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "model": model,
                        "temperature": temperature,
                        "tools_used": [],
                        "context_length": 1
                    }
                })
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            # Store failed execution
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            error_message = str(e)
            
            cursor.execute('''
                INSERT INTO executions (
                    id, agent_id, input_text, success, duration, error_message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_id, agent_id, input_text, False, duration, error_message, datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                "id": execution_id,
                "agentId": agent_id,
                "input": input_text,
                "output": "",
                "success": False,
                "duration": duration,
                "tokensUsed": 0,
                "error": error_message,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "model": agent_row[4],
                    "temperature": agent_row[8],
                    "tools_used": [],
                    "context_length": 0
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error executing agent: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/ollama/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    """Get agent performance metrics"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get execution statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_executions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_executions,
                AVG(duration) as avg_response_time,
                SUM(tokens_used) as total_tokens_used,
                MAX(timestamp) as last_execution
            FROM executions 
            WHERE agent_id = ?
        ''', (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:  # If there are executions
            return jsonify({
                "totalExecutions": row[0],
                "successfulExecutions": row[1],
                "failedExecutions": row[2],
                "averageResponseTime": row[3] or 0,
                "totalTokensUsed": row[4] or 0,
                "averageTokensPerExecution": (row[4] or 0) / row[0] if row[0] > 0 else 0,
                "lastExecution": row[5]
            })
        else:
            return jsonify({
                "totalExecutions": 0,
                "successfulExecutions": 0,
                "failedExecutions": 0,
                "averageResponseTime": 0,
                "totalTokensUsed": 0,
                "averageTokensPerExecution": 0,
                "lastExecution": None
            })
            
    except Exception as e:
        logger.error(f"Error getting agent metrics: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check Ollama status
        ollama_status = "unknown"
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            ollama_status = "running" if response.status_code == 200 else "error"
        except:
            ollama_status = "not_running"
        
        # Count agents
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM agents')
        agent_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM conversations')
        conversation_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM executions')
        execution_count = cursor.fetchone()[0]
        
        conn.close()
        
        errors = []
        if ollama_status != "running":
            errors.append("Ollama service is not running")
        
        status = "healthy" if len(errors) == 0 else ("degraded" if ollama_status == "running" else "unhealthy")
        
        return jsonify({
            "status": status,
            "ollamaStatus": ollama_status,
            "agentCount": agent_count,
            "activeConversations": conversation_count,
            "totalExecutions": execution_count,
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5052, debug=True)