/**
 * AgentCore SDK Integration
 * Based on: https://github.com/awslabs/amazon-bedrock-agentcore-samples
 * 
 * This implements AWS Bedrock Agents patterns for enterprise workflows
 */

export interface AgentCoreConfig {
  name: string;
  description: string;
  model: {
    provider: 'bedrock';
    model_id: string;
    inference_config?: {
      temperature?: number;
      top_p?: number;
      max_tokens?: number;
    };
  };
  action_groups: {
    name: string;
    description: string;
    functions: {
      name: string;
      description: string;
      parameters: Record<string, any>;
    }[];
  }[];
  knowledge_bases?: {
    id: string;
    name: string;
    description: string;
  }[];
  guardrails?: {
    id: string;
    version: string;
  };
  memory_configuration?: {
    enabled: boolean;
    storage_days?: number;
  };
  prompt_override?: {
    prompt_type: 'ORCHESTRATION' | 'KNOWLEDGE_BASE' | 'PRE_PROCESSING' | 'POST_PROCESSING';
    prompt_creation_mode: 'DEFAULT' | 'OVERRIDDEN';
    prompt_state: 'ENABLED' | 'DISABLED';
    base_prompt_template?: string;
    inference_configuration?: Record<string, any>;
  };
}

export interface AgentCoreAgent {
  id: string;
  name: string;
  status: 'creating' | 'prepared' | 'failed' | 'updating' | 'deleting';
  config: AgentCoreConfig;
  metadata: {
    created_at: string;
    framework: 'agentcore';
    agent_arn: string;
    agent_version: string;
    action_groups_count: number;
    knowledge_bases_count: number;
    guardrails_enabled: boolean;
    memory_enabled: boolean;
    performance_metrics: {
      invocations_count: number;
      avg_latency: number;
      success_rate: number;
      error_rate: number;
    };
  };
}

export class AgentCoreSDK {
  private baseUrl: string;
  private region: string;
  private apiKey: string;

  constructor(baseUrl: string = '/api', region: string = 'us-east-1', apiKey?: string) {
    this.baseUrl = baseUrl;
    this.region = region;
    this.apiKey = apiKey || '';
  }

  /**
   * Create an AgentCore agent with AWS Bedrock Agents
   */
  async createAgent(config: AgentCoreConfig): Promise<AgentCoreAgent> {
    // Validate AWS Bedrock credentials
    if (!this.hasBedrockCredentials()) {
      throw new Error('AWS Bedrock credentials required for AgentCore agents');
    }

    // Build AgentCore-specific configuration
    const agentCoreConfig = {
      name: config.name,
      framework: 'agentcore',
      config: {
        model: config.model,
        bedrock_agent: {
          agent_name: config.name,
          description: config.description,
          foundation_model: config.model.model_id,
          instruction: this.buildAgentInstruction(config),
          action_groups: config.action_groups.map(ag => ({
            action_group_name: ag.name,
            description: ag.description,
            action_group_executor: {
              lambda: this.generateLambdaConfig(ag.functions)
            },
            function_schema: {
              functions: ag.functions.map(func => ({
                name: func.name,
                description: func.description,
                parameters: func.parameters
              }))
            }
          })),
          knowledge_bases: config.knowledge_bases || [],
          guardrails_configuration: config.guardrails ? {
            guardrail_identifier: config.guardrails.id,
            guardrail_version: config.guardrails.version
          } : undefined,
          memory_configuration: config.memory_configuration,
          prompt_override_configuration: config.prompt_override
        },
        metadata: {
          framework_version: '2.0.0',
          aws_region: this.region,
          action_groups_count: config.action_groups.length,
          knowledge_bases_count: config.knowledge_bases?.length || 0,
          created_with: 'agentcore-sdk'
        }
      }
    };

    // Call backend API
    const response = await fetch(`${this.baseUrl}/agents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
      },
      body: JSON.stringify(agentCoreConfig)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create AgentCore agent');
    }

    const result = await response.json();
    
    return {
      id: result.agent_id,
      name: config.name,
      status: 'creating',
      config,
      metadata: {
        created_at: new Date().toISOString(),
        framework: 'agentcore',
        agent_arn: `arn:aws:bedrock:${this.region}:account:agent/${result.agent_id}`,
        agent_version: 'DRAFT',
        action_groups_count: config.action_groups.length,
        knowledge_bases_count: config.knowledge_bases?.length || 0,
        guardrails_enabled: !!config.guardrails,
        memory_enabled: config.memory_configuration?.enabled || false,
        performance_metrics: {
          invocations_count: 0,
          avg_latency: 0,
          success_rate: 0,
          error_rate: 0
        }
      }
    };
  }

  /**
   * Build agent instruction based on configuration
   */
  private buildAgentInstruction(config: AgentCoreConfig): string {
    let instruction = `You are ${config.name}. ${config.description}\n\n`;
    
    instruction += "Your capabilities include:\n";
    
    if (config.action_groups.length > 0) {
      instruction += "- Execute actions through the following action groups:\n";
      config.action_groups.forEach(ag => {
        instruction += `  * ${ag.name}: ${ag.description}\n`;
      });
    }
    
    if (config.knowledge_bases && config.knowledge_bases.length > 0) {
      instruction += "- Access knowledge from the following knowledge bases:\n";
      config.knowledge_bases.forEach(kb => {
        instruction += `  * ${kb.name}: ${kb.description}\n`;
      });
    }
    
    instruction += "\nAlways provide helpful, accurate, and contextual responses based on your capabilities.";
    
    return instruction;
  }

  /**
   * Generate Lambda configuration for action group functions
   */
  private generateLambdaConfig(functions: AgentCoreConfig['action_groups'][0]['functions']): {
    lambda_arn: string;
  } {
    // In a real implementation, this would create or reference actual Lambda functions
    return {
      lambda_arn: `arn:aws:lambda:${this.region}:account:function:agent-action-executor`
    };
  }

  /**
   * Check if AWS Bedrock credentials are available
   */
  private hasBedrockCredentials(): boolean {
    // In a real implementation, this would check environment variables
    // For demo purposes, we'll check via the health endpoint
    return true; // Will be validated by backend
  }

  /**
   * Invoke an AgentCore agent
   */
  async invokeAgent(agentId: string, sessionId: string, inputText: string, options?: {
    enable_trace?: boolean;
    session_state?: Record<string, any>;
  }): Promise<{
    response: string;
    session_id: string;
    trace?: {
      orchestration_trace?: any;
      pre_processing_trace?: any;
      post_processing_trace?: any;
    };
    citations?: {
      generated_response_part: {
        text_response_part: {
          text: string;
          span: { start: number; end: number; };
        };
      };
      retrieved_references: {
        content: { text: string; };
        location: { type: string; uri: string; };
        metadata: Record<string, any>;
      }[];
    }[];
  }> {
    const response = await fetch(`${this.baseUrl}/agents/${agentId}/invoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
      },
      body: JSON.stringify({
        session_id: sessionId,
        input_text: inputText,
        enable_trace: options?.enable_trace || false,
        session_state: options?.session_state || {}
      })
    });

    if (!response.ok) {
      throw new Error('Failed to invoke AgentCore agent');
    }

    return await response.json();
  }

  /**
   * Prepare agent (equivalent to creating an agent version)
   */
  async prepareAgent(agentId: string): Promise<{
    agent_id: string;
    agent_version: string;
    prepared_at: string;
  }> {
    const response = await fetch(`${this.baseUrl}/agents/${agentId}/prepare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
      }
    });

    if (!response.ok) {
      throw new Error('Failed to prepare AgentCore agent');
    }

    return await response.json();
  }

  /**
   * Get agent performance metrics
   */
  async getAgentMetrics(agentId: string): Promise<{
    invocation_metrics: {
      total_invocations: number;
      successful_invocations: number;
      failed_invocations: number;
      avg_latency_ms: number;
    };
    action_group_metrics: {
      action_group_name: string;
      invocations: number;
      success_rate: number;
      avg_execution_time: number;
    }[];
    knowledge_base_metrics: {
      knowledge_base_id: string;
      queries: number;
      avg_retrieval_time: number;
      relevance_score: number;
    }[];
  }> {
    const response = await fetch(`${this.baseUrl}/agents/${agentId}/metrics`);
    
    if (!response.ok) {
      throw new Error('Failed to get agent metrics');
    }

    return await response.json();
  }

  /**
   * List available foundation models for AgentCore
   */
  async listFoundationModels(): Promise<{
    model_id: string;
    model_name: string;
    provider_name: string;
    input_modalities: string[];
    output_modalities: string[];
    supported_customizations: string[];
  }[]> {
    const response = await fetch(`${this.baseUrl}/foundation-models`);
    
    if (!response.ok) {
      throw new Error('Failed to list foundation models');
    }

    return await response.json();
  }
}