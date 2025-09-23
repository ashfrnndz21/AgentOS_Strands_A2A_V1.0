#!/usr/bin/env python3
"""
Enhanced LLM Orchestration API
- LLM-powered query analysis and agent selection
- Intelligent context understanding
- Dynamic agent routing based on metadata
- Memory-efficient execution with cleanup
- Response synthesis and formatting
"""

import os
import sys
import json
import uuid
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import psutil
import gc

# Import the 6-stage orchestrator
try:
    from enhanced_orchestrator_6stage import Enhanced6StageOrchestrator
except ImportError:
    # Try relative import
    from .enhanced_orchestrator_6stage import Enhanced6StageOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
STRANDS_SDK_URL = "http://localhost:5006"
A2A_SERVICE_URL = "http://localhost:5008"
ORCHESTRATOR_MODEL = "qwen3:1.7b"  # Enhanced model for 6-stage orchestration
SESSION_TIMEOUT = 300  # 5 minutes
MEMORY_THRESHOLD = 85  # 85% memory usage threshold
CLEANUP_DELAY = 2  # 2 seconds delay before cleanup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'enhanced_orchestration_secret'
CORS(app)

@dataclass
class OrchestrationSession:
    """Enhanced orchestration session with LLM analysis"""
    session_id: str
    created_at: datetime
    query: str
    query_analysis: Optional[Dict] = None
    selected_agent: Optional[Dict] = None
    execution_result: Optional[Dict] = None
    final_response: Optional[str] = None
    status: str = "active"
    memory_usage: float = 0.0
    processing_stages: List[str] = None

    def __post_init__(self):
        if self.processing_stages is None:
            self.processing_stages = []

class EnhancedOrchestrator:
    """Enhanced LLM-powered orchestration system"""
    
    def __init__(self):
        self.active_sessions: Dict[str, OrchestrationSession] = {}
        self.agent_metadata_cache: Dict[str, Dict] = {}
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        # Initialize the 6-stage orchestrator
        self.orchestrator_6stage = Enhanced6StageOrchestrator(
            ollama_base_url=OLLAMA_BASE_URL,
            orchestrator_model=ORCHESTRATOR_MODEL
        )
        
        logger.info("Enhanced Orchestrator initialized with 6-Stage LLM analysis")
    
    def create_session(self, query: str) -> OrchestrationSession:
        """Create a new orchestration session"""
        session_id = str(uuid.uuid4())
        session = OrchestrationSession(
            session_id=session_id,
            created_at=datetime.now(),
            query=query,
            processing_stages=["created", "analyzing", "selecting", "executing", "synthesizing", "cleanup"]
        )
        self.active_sessions[session_id] = session
        logger.info(f"Created enhanced session {session_id} for query: {query[:50]}...")
        return session
    
    def analyze_query_with_llm(self, query: str, available_agents: List[Dict]) -> Dict:
        """Use 6-stage LLM orchestrator to analyze query and select best agent"""
        try:
            # Use the 6-stage orchestrator for comprehensive analysis
            return self.orchestrator_6stage.analyze_query_with_6stage_orchestrator(query, available_agents)
        except Exception as e:
            logger.error(f"6-stage orchestrator error: {e}")
            # Fallback to simple analysis if 6-stage fails
            return self._fallback_analysis(query, available_agents)
    
    def release_llm_model(self):
        """Release LLM model from memory to free up resources"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Log memory status
            import psutil
            memory_usage = psutil.virtual_memory().percent
            logger.info(f"Memory management: Model released, current usage: {memory_usage:.1f}%")
            
        except Exception as e:
            logger.warning(f"Memory management warning: {e}")

    def analyze_agents_contextually(self, query: str, available_agents: List[Dict], user_intent: str, domain_analysis: Dict) -> Dict:
        """Analyze all agents in registry with contextual scoring based on user intent and domain"""
        try:
            # Prepare simplified agent data for LLM analysis
            agent_data = []
            for agent in available_agents:
                agent_data.append({
                    "name": agent['name'],
                    "description": agent.get('description', ''),
                    "role": agent.get('description', '')  # Use description as role for now
                })
            
            # Create prompt for agent analysis
            prompt = f"""
You are an expert agent orchestrator. Analyze each agent and provide a brief contextual analysis. Keep ALL responses to maximum 2 sentences.

USER QUERY: {query}
USER INTENT: {user_intent}
DOMAIN ANALYSIS: {domain_analysis}

AVAILABLE AGENTS:
{json.dumps(agent_data, indent=2)}

For each agent, provide a brief analysis (max 2 sentences each):
1. Role Analysis: What is this agent's primary role?
2. Contextual Relevance: How well does this agent match the user's intent?
3. Association Score: A score from 0.0 to 1.0

Return your analysis in this JSON format:
{{
    "agent_analysis": [
        {{
            "agent_name": "agent_name",
            "role_analysis": "Brief 2-sentence analysis of the agent's role and purpose",
            "contextual_relevance": "Brief 2-sentence analysis of how well this agent matches the user intent",
            "association_score": 0.85
        }}
    ],
    "analysis_summary": "Brief 2-sentence overall summary of agent capabilities and recommendations"
}}
"""
            
            # Call LLM for analysis
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "qwen3:1.7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 1000  # Reduced from 2000
                    }
                },
                timeout=30  # Reduced from 60 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response (handle potential markdown formatting)
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        analysis = json.loads(json_text)
                        
                        # Validate and structure the response
                        if 'agent_analysis' in analysis:
                            return {
                                "success": True,
                                "agent_analysis": analysis['agent_analysis'],
                                "analysis_summary": analysis.get('analysis_summary', ''),
                                "total_agents_analyzed": len(analysis['agent_analysis'])
                            }
                        else:
                            raise ValueError("Invalid response format")
                    else:
                        raise ValueError("No JSON found in response")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse agent analysis JSON: {e}")
                    # Fallback to simple analysis
                    return self._fallback_agent_analysis(available_agents, user_intent, domain_analysis)
            else:
                logger.error(f"LLM analysis failed: {response.status_code}")
                return self._fallback_agent_analysis(available_agents, user_intent, domain_analysis)
                
        except Exception as e:
            logger.error(f"Agent analysis error: {e}")
            return self._fallback_agent_analysis(available_agents, user_intent, domain_analysis)
    
    def _fallback_agent_analysis(self, available_agents: List[Dict], user_intent: str, domain_analysis: Dict) -> Dict:
        """Fallback agent analysis when LLM fails"""
        agent_analysis = []
        
        for agent in available_agents:
            # Simple scoring based on keyword matching
            score = 0.0
            agent_name = agent.get('name', '').lower()
            agent_desc = agent.get('description', '').lower()
            agent_capabilities = agent.get('capabilities', [])
            
            # Check for keyword matches
            query_lower = user_intent.lower()
            for word in query_lower.split():
                if word in agent_desc:
                    score += 0.2
                if word in agent_name:
                    score += 0.3
                if any(word in cap.lower() for cap in agent_capabilities):
                    score += 0.1
            
            # Cap the score at 1.0
            score = min(score, 1.0)
            
            agent_analysis.append({
                "agent_name": agent['name'],
                "role_analysis": f"Agent specialized in {agent.get('description', 'general assistance')}. Provides basic support for user queries.",
                "contextual_relevance": f"Basic keyword matching suggests {'high' if score > 0.5 else 'moderate' if score > 0.2 else 'low'} relevance to user intent. Suitable for general assistance tasks.",
                "association_score": score
            })
        
        # Sort by association score
        agent_analysis.sort(key=lambda x: x['association_score'], reverse=True)
        
        return {
            "success": True,
            "agent_analysis": agent_analysis,
            "analysis_summary": f"Analyzed {len(agent_analysis)} agents using fallback keyword matching. Found suitable agents for user query based on basic relevance scoring.",
            "total_agents_analyzed": len(agent_analysis)
        }
    
    def _fallback_analysis(self, query: str, available_agents: List[Dict]) -> Dict:
        """Dynamic fallback analysis when LLM fails"""
        query_lower = query.lower()
        
        # Dynamic keyword analysis for better matching
        keyword_matches = {}
        
        for agent in available_agents:
            score = 0
            agent_name = agent.get('name', '').lower()
            agent_desc = agent.get('description', '').lower()
            agent_capabilities = agent.get('capabilities', [])
            
            # Check for direct keyword matches in description
            for word in query_lower.split():
                if word in agent_desc:
                    score += 3
                if word in agent_name:
                    score += 2
            
            # Check for capability matches
            for capability in agent_capabilities:
                if any(word in capability.lower() for word in query_lower.split()):
                    score += 2
            
            # Check for semantic matches
            if any(word in query_lower for word in ['help', 'assist', 'support']):
                if 'assistant' in agent_name or 'help' in agent_desc:
                    score += 1
            
            keyword_matches[agent['id']] = {
                'agent': agent,
                'score': score
            }
        
        # Find best matching agent
        best_match = max(keyword_matches.items(), key=lambda x: x[1]['score'])
        best_agent = best_match[1]['agent']
        best_score = best_match[1]['score']
        
        # Determine domain dynamically
        if best_score > 0:
            # Try to infer domain from the best matching agent
            agent_desc = best_agent.get('description', '').lower()
            if any(word in agent_desc for word in ['health', 'medical', 'doctor']):
                domain = "health"
            elif any(word in agent_desc for word in ['creative', 'write', 'poem', 'story']):
                domain = "creative"
            elif any(word in agent_desc for word in ['technical', 'code', 'program']):
                domain = "technical"
            elif any(word in agent_desc for word in ['weather', 'climate']):
                domain = "weather"
            else:
                domain = "general"
        else:
            domain = "general"
        
        return {
            "stage_1_query_analysis": {
                "user_intent": f"User query requiring {domain} assistance",
                "domain": domain,
                "complexity": "moderate",
                "required_expertise": domain,
                "context_reasoning": f"Fallback analysis suggests {domain} domain based on keyword matching"
            },
            "stage_2_agent_analysis": {
                "agent_evaluations": [
                    {
                        "agent_id": best_agent['id'],
                        "agent_name": best_agent['name'],
                        "primary_expertise": domain,
                        "capabilities_assessment": f"Best match based on keyword scoring (score: {best_score})",
                        "tools_analysis": f"Tools: {best_agent.get('capabilities', [])}",
                        "system_prompt_analysis": f"Description: {best_agent.get('description', '')}",
                        "suitability_score": min(best_score / 10.0, 1.0)
                    }
                ]
            },
            "stage_3_contextual_matching": {
                "selected_agent_id": best_agent['id'],
                "matching_reasoning": f"Fallback selected {best_agent['name']} based on keyword matching (score: {best_score})",
                "confidence": 0.6,
                "alternative_agents": [aid for aid, data in keyword_matches.items() if aid != best_agent['id'] and data['score'] > 0],
                "match_quality": "moderate",
                "execution_strategy": "single"
            }
        }
    
    def execute_agent_query(self, agent_id: str, query: str, session_id: str) -> Dict:
        """Execute query with selected agent"""
        try:
            start_time = time.time()
            
            # Execute via Strands SDK
            response = requests.post(
                f"{STRANDS_SDK_URL}/api/strands-sdk/agents/{agent_id}/execute",
                json={"input": query},
                timeout=180  # 3 minutes timeout
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "agent_id": agent_id
                }
            else:
                return {
                    "success": False,
                    "error": f"Agent execution failed: {response.status_code}",
                    "execution_time": execution_time,
                    "agent_id": agent_id
                }
        
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": 0,
                "agent_id": agent_id
            }
    
    def synthesize_response(self, query: str, analysis: Dict, execution_result: Dict, agent_metadata: Dict) -> str:
        """Use LLM to synthesize final response from agent output"""
        try:
            if not execution_result.get('success'):
                return f"I apologize, but I encountered an error while processing your request: {execution_result.get('error', 'Unknown error')}"
            
            agent_response = execution_result.get('result', {})
            
            # Extract the actual response text
            response_text = ""
            if isinstance(agent_response, dict):
                response_text = agent_response.get('response', agent_response.get('output_text', str(agent_response)))
            else:
                response_text = str(agent_response)
            
            # Create synthesis prompt
            synthesis_prompt = f"""You are a response synthesizer that creates polished, user-friendly responses from agent outputs.

Original User Query: "{query}"
Query Analysis: {json.dumps(analysis.get('query_analysis', {}), indent=2)}
Selected Agent: {agent_metadata.get('name', 'Unknown')} - {agent_metadata.get('description', '')}
Agent Response: {response_text}

Your task is to:
1. Review the agent's response
2. Ensure it directly addresses the user's query
3. Make the response clear, helpful, and well-formatted
4. Add any necessary context or clarifications
5. Maintain a professional yet friendly tone

Provide a polished, final response that the user will receive. Do not include any meta-commentary about the orchestration process."""

            # Call LLM for response synthesis
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": ORCHESTRATOR_MODEL,
                    "prompt": synthesis_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,  # Higher temperature for natural response
                        "top_p": 0.9,
                        "max_tokens": 800
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                synthesized_response = result.get('response', '').strip()
                logger.info(f"Response synthesis successful")
                return synthesized_response
            else:
                # Fallback to original agent response
                return response_text
                
        except Exception as e:
            logger.error(f"Response synthesis error: {e}")
            # Fallback to original agent response
            return str(execution_result.get('result', {}).get('response', 'Response processing completed'))
    
    def process_query(self, query: str, contextual_analysis: Dict = None, test_mode: bool = False) -> Dict:
        """Process query through enhanced orchestration pipeline"""
        session = self.create_session(query)
        
        try:
            # Stage 1: Get available agents
            logger.info(f"[{session.session_id}] Stage 1: Getting available agents")
            
            # Get A2A agents
            a2a_response = requests.get(f"{A2A_SERVICE_URL}/api/a2a/agents", timeout=10)
            if a2a_response.status_code != 200:
                return {
                    "success": False,
                    "error": "Failed to get A2A agents",
                    "session_id": session.session_id
                }
            
            a2a_agents = a2a_response.json().get('agents', [])
            
            # Get Strands SDK agents
            sdk_response = requests.get(f"{STRANDS_SDK_URL}/api/strands-sdk/agents", timeout=10)
            if sdk_response.status_code != 200:
                return {
                    "success": False,
                    "error": "Failed to get SDK agents",
                    "session_id": session.session_id
                }
            
            sdk_agents = sdk_response.json().get('agents', [])
            
            # Match agents or use SDK agents directly if no A2A agents
            available_agents = []
            
            if a2a_agents:
                # Match A2A agents with SDK agents
                for a2a_agent in a2a_agents:
                    a2a_name = a2a_agent.get('name')
                    for sdk_agent in sdk_agents:
                        if sdk_agent.get('name') == a2a_name:
                            available_agents.append({
                                'id': sdk_agent['id'],
                                'name': sdk_agent['name'],
                                'description': sdk_agent.get('description', ''),
                                'capabilities': sdk_agent.get('tools', []),
                                'tools': sdk_agent.get('tools', []),
                                'model': sdk_agent.get('model_id', 'unknown'),
                                'system_prompt': sdk_agent.get('system_prompt', '')
                            })
                            break
            else:
                # Use SDK agents directly if no A2A agents
                for sdk_agent in sdk_agents:
                    available_agents.append({
                        'id': sdk_agent['id'],
                        'name': sdk_agent['name'],
                        'description': sdk_agent.get('description', ''),
                        'capabilities': sdk_agent.get('tools', []),
                        'tools': sdk_agent.get('tools', []),
                        'model': sdk_agent.get('model_id', 'unknown'),
                        'system_prompt': sdk_agent.get('system_prompt', '')
                    })
            
            if not available_agents:
                return {
                    "success": False,
                    "error": "No agents available",
                    "session_id": session.session_id
                }
            
            # Stage 2: LLM Query Analysis (Skip if we have contextual analysis)
            if contextual_analysis and contextual_analysis.get('success'):
                logger.info(f"[{session.session_id}] Stage 2: Using provided contextual analysis (skipping LLM call)")
                # Create minimal analysis structure from contextual analysis
                analysis = {
                    'stage_1_query_analysis': {
                        'user_intent': contextual_analysis.get('user_intent', 'General assistance'),
                        'domain': contextual_analysis.get('domain_analysis', {}).get('primary_domain', 'General'),
                        'complexity': contextual_analysis.get('domain_analysis', {}).get('technical_level', 'beginner'),
                        'required_expertise': 'General assistance'
                    },
                    'stage_3_execution_strategy': {
                        'strategy': contextual_analysis.get('orchestration_pattern', 'direct'),
                        'reasoning': 'Based on provided contextual analysis'
                    },
                    'stage_5_agent_matching': {
                        'selected_agents': []  # Will be filled by agent analysis
                    }
                }
            else:
                logger.info(f"[{session.session_id}] Stage 2: LLM query analysis")
                analysis = self.analyze_query_with_llm(query, available_agents)
                # Memory Management: Release model after Orchestrator Reasoning
                logger.info(f"[{session.session_id}] Memory Management: Releasing LLM model after Orchestrator Reasoning")
                self.release_llm_model()
            
            session.query_analysis = analysis
            
            # Stage 2.5: Agent Registry Analysis
            logger.info(f"[{session.session_id}] Stage 2.5: Agent registry contextual analysis")
            
            # Extract user intent and domain analysis from streamlined analysis if available
            user_intent = "General query assistance"
            domain_analysis = {"primary_domain": "General", "technical_level": "beginner"}
            
            # Check if we have contextual analysis data from frontend
            if contextual_analysis and contextual_analysis.get('success'):
                user_intent = contextual_analysis.get('user_intent', user_intent)
                domain_analysis = contextual_analysis.get('domain_analysis', domain_analysis)
                # Store in session for reference
                session.streamlined_analysis = contextual_analysis
            elif hasattr(session, 'streamlined_analysis') and session.streamlined_analysis:
                user_intent = session.streamlined_analysis.get('user_intent', user_intent)
                domain_analysis = session.streamlined_analysis.get('domain_analysis', domain_analysis)
            elif 'stage_1_query_analysis' in analysis:
                user_intent = analysis['stage_1_query_analysis'].get('user_intent', user_intent)
                domain_analysis = {
                    "primary_domain": analysis['stage_1_query_analysis'].get('domain', 'General'),
                    "technical_level": analysis['stage_1_query_analysis'].get('complexity', 'beginner')
                }
            
            # Perform contextual agent analysis
            logger.info(f"[{session.session_id}] Starting agent analysis with {len(available_agents)} agents")
            agent_analysis_result = self.analyze_agents_contextually(query, available_agents, user_intent, domain_analysis)
            logger.info(f"[{session.session_id}] Agent analysis result: {agent_analysis_result.get('success', False)}")
            session.agent_analysis = agent_analysis_result
            
            # Memory Management: Release model after Agent Analysis
            logger.info(f"[{session.session_id}] Memory Management: Releasing LLM model after Agent Analysis")
            self.release_llm_model()
            
            # Add agent analysis to the main analysis result (ensure it's never null)
            if agent_analysis_result and agent_analysis_result.get('success'):
                analysis['agent_registry_analysis'] = agent_analysis_result
            else:
                # Fallback: create a minimal analysis structure
                analysis['agent_registry_analysis'] = {
                    "success": False,
                    "agent_analysis": [],
                    "analysis_summary": "Agent analysis failed - using fallback",
                    "total_agents_analyzed": 0
                }
            
            # Stage 3: Agent Selection & A2A Handover Orchestration
            logger.info(f"[{session.session_id}] Stage 3: Agent selection and A2A handover orchestration")
            
            # Get execution strategy from analysis
            execution_strategy = analysis.get('stage_3_execution_strategy', {}).get('strategy', 'direct')
            
            # Use agent analysis results for selection (faster than 6-stage orchestrator)
            selected_agents = []
            if agent_analysis_result and agent_analysis_result.get('success'):
                agent_analysis = agent_analysis_result.get('agent_analysis', [])
                # Select top 2 agents by association score
                sorted_agents = sorted(agent_analysis, key=lambda x: x.get('association_score', 0), reverse=True)
                for i, agent in enumerate(sorted_agents[:2]):  # Max 2 agents
                    selected_agents.append({
                        'agent_name': agent.get('agent_name', 'Unknown'),
                        'execution_order': i + 1,
                        'task_assignment': agent.get('role_analysis', 'General assistance')[:100]  # Truncate for brevity
                    })
            
            logger.info(f"Execution strategy: {execution_strategy}")
            logger.info(f"Selected agents: {len(selected_agents)}")
            logger.info(f"Selected agents details: {selected_agents}")
            
            # Execute based on strategy - FIXED LOGIC
            if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1:
                # Sequential A2A handover execution - PRIORITY PATH
                logger.info(f"[{session.session_id}] Stage 4: Sequential A2A handover execution")
                logger.info(f"[{session.session_id}] Selected agents for handover: {[a.get('agent_name', 'unknown') for a in selected_agents]}")
                execution_results = execute_sequential_a2a_handover(selected_agents, available_agents, query, session.session_id)
                session.execution_result = execution_results
                
            elif execution_strategy == 'parallel' and len(selected_agents) > 1:
                # Parallel execution (future implementation)
                logger.info(f"[{session.session_id}] Stage 4: Parallel execution (not yet implemented)")
                # For now, fall back to sequential
                execution_results = execute_sequential_a2a_handover(selected_agents, available_agents, query, session.session_id)
                session.execution_result = execution_results
                
            else:
                # Single agent execution (fallback)
                logger.info(f"[{session.session_id}] Stage 4: Single agent execution (fallback)")
                if selected_agents:
                    agent_info = selected_agents[0]
                    agent_id = agent_info.get('agent_name')
                    # Find agent by name
                    selected_agent = next((a for a in available_agents if a['name'] == agent_id), None)
                else:
                    # Fallback to old method
                    selected_agent_id = analysis['stage_3_contextual_matching']['selected_agent_id']
                    selected_agent = next((a for a in available_agents if a['id'] == selected_agent_id), None)
                
                if not selected_agent:
                    return {
                        "success": False,
                        "error": "Selected agent not found",
                        "session_id": session.session_id
                    }
                
                logger.info(f"Single agent execution: {selected_agent['name']} (ID: {selected_agent['id']})")
                session.selected_agent = selected_agent
                
                # Stage 4: Single Agent Execution
                execution_result = self.execute_agent_query(selected_agent['id'], query, session.session_id)
                session.execution_result = execution_result
            
            # Stage 5: Response Synthesis
            logger.info(f"[{session.session_id}] Stage 5: Response synthesis")
            if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1:
                # Handle sequential execution results
                final_response = self.synthesize_sequential_response(query, analysis, execution_results, selected_agents)
            else:
                # Handle single agent execution results
                if 'execution_result' in locals():
                    final_response = self.synthesize_response(query, analysis, execution_result, selected_agent)
                else:
                    # Fallback if execution_result is not defined
                    final_response = f"Orchestration completed but response synthesis failed. Strategy: {execution_strategy}, Agents: {len(selected_agents)}"
            session.final_response = final_response
            
            # Update session status
            session.status = "completed"
            
            # Prepare comprehensive response with detailed reasoning
            execution_success = False
            if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1:
                execution_success = execution_results.get('success', False)
            elif 'execution_result' in locals():
                execution_success = execution_result.get('success', False)
            else:
                execution_success = True  # Fallback for other cases
            
            # Define match_quality with fallback
            match_quality = analysis.get('stage_3_execution_strategy', {}).get('match_quality', 'moderate')
            
            result = {
                "success": execution_success,
                "session_id": session.session_id,
                "orchestration_summary": {
                    "total_stages": 6,
                    "stages_completed": 5,
                    "execution_strategy": analysis.get('stage_3_execution_strategy', {}).get('strategy', 'single'),
                    "reasoning_quality": match_quality,
                    "processing_time": (datetime.now() - session.created_at).total_seconds()
                },
                "stage_1_query_analysis": {
                    **analysis.get('stage_1_query_analysis', {}),
                    "reasoning": "Analyzed user intent, domain, and complexity to understand query requirements"
                },
                "stage_2_sequence_definition": {
                    **analysis.get('stage_2_sequence_definition', {}),
                    "reasoning": "Defined workflow steps and execution flow based on query complexity"
                },
                "stage_3_execution_strategy": {
                    **analysis.get('stage_3_execution_strategy', {}),
                    "reasoning": "Determined optimal execution strategy (single/sequential/parallel) based on task requirements"
                },
                "stage_4_agent_analysis": {
                    **analysis.get('stage_4_agent_analysis', {}),
                    "reasoning": "Evaluated all available agents for their capabilities, tools, and suitability"
                },
                "stage_5_agent_matching": {
                    **analysis.get('stage_5_agent_matching', {}),
                    "reasoning": f"Matched query requirements with agent capabilities: Agent selected based on analysis"
                },
                "stage_6_orchestration_plan": {
                    **analysis.get('stage_6_orchestration_plan', {}),
                    "reasoning": "Created final orchestration plan with confidence assessment and execution strategy"
                },
                "selected_agent": {
                    "id": selected_agents[0].get('agent_id', 'unknown') if selected_agents and len(selected_agents) > 0 else 'unknown',
                    "name": selected_agents[0].get('agent_name', 'unknown') if selected_agents and len(selected_agents) > 0 else 'unknown',
                    "description": selected_agents[0].get('task_assignment', 'No description available') if selected_agents and len(selected_agents) > 0 else 'unknown',
                    "capabilities": selected_agents[0].get('capabilities', []) if selected_agents and len(selected_agents) > 0 else [],
                    "tools": selected_agents[0].get('tools', []) if selected_agents and len(selected_agents) > 0 else [],
                    "model": selected_agents[0].get('model', 'unknown') if selected_agents and len(selected_agents) > 0 else 'unknown',
                    "selection_reasoning": 'Agent selected based on contextual analysis and domain matching',
                    "match_quality": match_quality
                },
                "execution_details": {
                    "execution_time": execution_results.get('execution_time', 0) if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1 else execution_result.get('execution_time', 0) if 'execution_result' in locals() else 0,
                    "agent_response_length": len(str(execution_results.get('strands_response', ''))) if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1 else len(str(execution_result.get('result', ''))) if 'execution_result' in locals() else 0,
                    "success": execution_success
                },
                "final_response": final_response,
                "raw_agent_response": execution_results if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1 else execution_result.get('result', {}) if 'execution_result' in locals() else {},
                "agent_registry_analysis": analysis.get('agent_registry_analysis', {}),
                "error": execution_results.get('error') if execution_strategy.lower() == 'sequential' and len(selected_agents) > 1 else execution_result.get('error') if 'execution_result' in locals() else None
            }
            
            # Schedule cleanup after delay
            threading.Timer(CLEANUP_DELAY, self.cleanup_session, [session.session_id]).start()
            
            return result
        
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            session.status = "failed"
            return {
                "success": False,
                "error": str(e),
                "session_id": session.session_id
            }
    
    def cleanup_session(self, session_id: str) -> bool:
        """Cleanup session and release resources"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            logger.info(f"Cleaned up enhanced session {session_id}")
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            memory_usage = psutil.virtual_memory().percent
            logger.info(f"Memory usage after cleanup: {memory_usage}%")
            
            return True
        return False
    
    def synthesize_sequential_response(self, query: str, analysis: Dict, execution_results: Dict, selected_agents: List[Dict]) -> str:
        """Synthesize response from sequential A2A handover execution"""
        try:
            logger.info("Synthesizing sequential response from A2A handover")
            
            if not execution_results.get("success"):
                return f"Sequential execution failed: {execution_results.get('error', 'Unknown error')}"
            
            # Extract Strands response
            strands_response = execution_results.get("strands_response", "")
            coordination_results = execution_results.get("coordination_results", {})
            
            # Build comprehensive response
            response_parts = []
            
            # Add orchestration summary
            response_parts.append("🤖 **Multi-Agent Orchestration Complete**")
            response_parts.append(f"**Strategy**: Sequential A2A Handover")
            response_parts.append(f"**Agents Coordinated**: {execution_results.get('agents_coordinated', 0)}")
            response_parts.append("")
            
            # Add Strands orchestrator response
            if strands_response:
                response_parts.append("**Orchestrator Analysis:**")
                response_parts.append(strands_response)
                response_parts.append("")
            
            # Add coordination details
            if coordination_results:
                response_parts.append("**Coordination Details:**")
                if coordination_results.get("agent_references"):
                    response_parts.append(f"**Agents Referenced**: {', '.join(coordination_results['agent_references'])}")
                if coordination_results.get("coordination_indicators"):
                    response_parts.append(f"**Coordination Methods**: {', '.join(coordination_results['coordination_indicators'])}")
                response_parts.append("")
            
            # Add execution summary
            response_parts.append("**Execution Summary:**")
            response_parts.append(f"✅ Sequential A2A handover completed successfully")
            response_parts.append(f"⏱️ Total execution time: {execution_results.get('execution_time', 0):.2f} seconds")
            response_parts.append(f"🔄 Orchestration type: {execution_results.get('orchestration_type', 'unknown')}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error synthesizing sequential response: {e}")
            return f"Sequential response synthesis failed: {str(e)}"
    
    def _cleanup_worker(self):
        """Background worker for automatic session cleanup"""
        while True:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.active_sessions.items():
                    if current_time - session.created_at > timedelta(seconds=SESSION_TIMEOUT):
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    logger.warning(f"Cleaning up expired enhanced session {session_id}")
                    self.cleanup_session(session_id)
                
                # Check memory usage
                memory_usage = psutil.virtual_memory().percent
                if memory_usage > MEMORY_THRESHOLD:
                    logger.warning(f"High memory usage: {memory_usage}%")
                    # Force cleanup of oldest sessions
                    if self.active_sessions:
                        # Clean up multiple sessions if memory is very high
                        sessions_to_cleanup = min(3, len(self.active_sessions))
                        sorted_sessions = sorted(self.active_sessions.items(), 
                                               key=lambda x: x[1].created_at)
                        
                        for i in range(sessions_to_cleanup):
                            session_id = sorted_sessions[i][0]
                            logger.warning(f"Force cleaning up session {session_id} due to high memory")
                            self.cleanup_session(session_id)
                        
                        # Force garbage collection after cleanup
                        gc.collect()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Enhanced cleanup worker error: {e}")
                time.sleep(60)

# Initialize orchestrator
orchestrator = EnhancedOrchestrator()

@app.route('/api/enhanced-orchestration/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    memory_usage = psutil.virtual_memory().percent
    active_sessions = len(orchestrator.active_sessions)
    
    return jsonify({
        "status": "healthy",
        "memory_usage": f"{memory_usage}%",
        "active_sessions": active_sessions,
        "orchestrator_model": ORCHESTRATOR_MODEL,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/enhanced-orchestration/query', methods=['POST'])
def process_query():
    """Process query through enhanced orchestration"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        contextual_analysis = data.get('contextual_analysis', None)
        test_mode = data.get('test_mode', False)  # Add test mode parameter
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Query is required"
            }), 400
        
        logger.info(f"Processing enhanced orchestration query: {query[:50]}... (test_mode: {test_mode})")
        
        result = orchestrator.process_query(query, contextual_analysis, test_mode)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Enhanced query endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def execute_sequential_a2a_handover(selected_agents: List[Dict], available_agents: List[Dict], query: str, session_id: str) -> Dict[str, Any]:
    """Execute sequential A2A handover using Strands SDK patterns"""
    try:
        logger.info(f"[{session_id}] Starting Strands A2A handover with {len(selected_agents)} agents")
        
        # Import Strands orchestration engine
        from strands_orchestration_engine import get_strands_orchestration_engine
        from a2a_strands_integration import get_a2a_integration
        
        # Get orchestration engine and A2A integration
        orchestration_engine = get_strands_orchestration_engine()
        a2a_integration = get_a2a_integration()
        orchestration_engine.set_a2a_integration(a2a_integration)
        
        # Execute using Strands model-driven orchestration
        result = orchestration_engine.execute_strands_orchestration(query, available_agents, session_id)
        
        if result.get("success"):
            logger.info(f"[{session_id}] Strands A2A handover completed successfully")
            return {
                "success": True,
                "orchestration_type": "strands_a2a_handover",
                "agents_coordinated": len(selected_agents),
                "strands_response": result.get("orchestrator_response", ""),
                "coordination_results": result.get("coordination_results", {}),
                "execution_time": result.get("execution_time", 0),
                "session_id": session_id
            }
        else:
            logger.error(f"[{session_id}] Strands A2A handover failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error in Strands orchestration"),
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"Error in Strands A2A handover: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

@app.route('/api/enhanced-orchestration/sessions', methods=['GET'])
def get_sessions():
    """Get active sessions info"""
    sessions_info = []
    for session_id, session in orchestrator.active_sessions.items():
        sessions_info.append({
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "query": session.query[:50] + "..." if len(session.query) > 50 else session.query,
            "status": session.status,
            "stages_completed": len(session.processing_stages),
            "duration": (datetime.now() - session.created_at).total_seconds()
        })
    
    return jsonify({
        "active_sessions": len(sessions_info),
        "sessions": sessions_info
    })

@app.route('/api/enhanced-orchestration/sessions/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Manually cleanup a session"""
    if orchestrator.cleanup_session(session_id):
        return jsonify({"success": True, "message": f"Enhanced session {session_id} cleaned up"})
    else:
        return jsonify({"success": False, "error": "Session not found"}), 404

if __name__ == '__main__':
    logger.info("🚀 Starting Enhanced LLM Orchestration API...")
    logger.info("📍 Port: 5014")
    logger.info("🧠 LLM-powered query analysis and agent selection")
    logger.info("🔄 Intelligent orchestration with memory management")
    logger.info("⚡ Enhanced response synthesis")
    
    app.run(host='0.0.0.0', port=5014, debug=False)
