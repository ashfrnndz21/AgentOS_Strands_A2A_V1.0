/**
 * MCP Gateway Service
 * Handles communication with the MCP Gateway Registry for server and tool management
 */

export interface MCPServer {
  id: string;
  name: string;
  description: string;
  url: string;
  status: 'connected' | 'disconnected' | 'testing' | 'error';
  type: 'local' | 'remote' | 'aws' | 'gateway';
  transport: 'sse' | 'streamable-http' | 'auto';
  supportedTransports: string[];
  toolCount: number;
  categories: string[];
  tags: string[];
  stars: number;
  license: string;
  isPython: boolean;
  enabled: boolean;
  authentication: {
    type: 'none' | 'bearer' | 'oauth2' | 'cognito';
    config?: any;
  };
  agentCompatibility?: {
    frameworks: string[];
    minVersion?: string;
    maxConcurrency?: number;
  };
  lastHealthCheck?: Date;
}

export interface MCPTool {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, any>;
  category: 'math' | 'text' | 'data' | 'api' | 'aws' | 'git' | 'filesystem' | 'other';
  serverId: string;
  serverName: string;
  popularity: number;
  verified: boolean;
  agentRecommended?: boolean;
  usageComplexity: 'simple' | 'moderate' | 'advanced';
  requiredPermissions?: string[];
}

export interface ToolSearchFilters {
  category?: string;
  serverType?: string;
  verified?: boolean;
  agentRecommended?: boolean;
  complexity?: string;
  minPopularity?: number;
}

export interface AgentToolBinding {
  agentId: string;
  toolId: string;
  serverId: string;
  configuration?: any;
  permissions: string[];
  enabled: boolean;
  createdAt: Date;
}

class MCPGatewayService {
  private baseUrl: string;
  private apiKey?: string;
  private servers: MCPServer[] = [];
  private tools: MCPTool[] = [];

  constructor(baseUrl: string = 'http://localhost:7860', apiKey?: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.loadFromStorage();
  }

  /**
   * Load servers and tools from localStorage
   */
  private loadFromStorage() {
    try {
      const savedServers = localStorage.getItem('mcp-gateway-servers');
      const savedTools = localStorage.getItem('mcp-gateway-tools');
      
      if (savedServers) {
        this.servers = JSON.parse(savedServers);
      } else {
        // Initialize with mock data if no saved data
        this.servers = this.getMockServers();
        this.saveToStorage();
      }
      
      if (savedTools) {
        this.tools = JSON.parse(savedTools);
      } else {
        // Generate tools from servers
        this.refreshToolsFromServers();
      }
    } catch (error) {
      console.error('Failed to load from storage:', error);
      this.servers = this.getMockServers();
      this.refreshToolsFromServers();
    }
  }

  /**
   * Save servers and tools to localStorage
   */
  private saveToStorage() {
    try {
      localStorage.setItem('mcp-gateway-servers', JSON.stringify(this.servers));
      localStorage.setItem('mcp-gateway-tools', JSON.stringify(this.tools));
    } catch (error) {
      console.error('Failed to save to storage:', error);
    }
  }

  /**
   * Refresh tools from all connected servers
   */
  private refreshToolsFromServers() {
    this.tools = [];
    for (const server of this.servers) {
      if (server.status === 'connected') {
        const serverTools = this.getMockToolsForServer(server.id);
        this.tools = [...this.tools, ...serverTools];
      }
    }
    this.saveToStorage();
  }

  /**
   * Get all registered MCP servers from the gateway
   */
  async getServers(): Promise<MCPServer[]> {
    try {
      return [...this.servers];
    } catch (error) {
      console.error('Failed to fetch MCP servers:', error);
      throw error;
    }
  }

  /**
   * Get all available tools from connected servers
   */
  async getTools(filters?: ToolSearchFilters): Promise<MCPTool[]> {
    try {
      let allTools = [...this.tools];

      // Apply filters
      if (filters) {
        allTools = this.filterTools(allTools, filters);
      }

      return allTools;
    } catch (error) {
      console.error('Failed to fetch MCP tools:', error);
      throw error;
    }
  }

  /**
   * Search tools using semantic search
   */
  async searchTools(query: string, filters?: ToolSearchFilters): Promise<MCPTool[]> {
    try {
      const allTools = await this.getTools(filters);
      
      // Simple text-based search for now. In production, this would use semantic search
      const searchResults = allTools.filter(tool => 
        tool.name.toLowerCase().includes(query.toLowerCase()) ||
        tool.description.toLowerCase().includes(query.toLowerCase()) ||
        tool.category.toLowerCase().includes(query.toLowerCase())
      );

      // Sort by relevance (popularity for now)
      return searchResults.sort((a, b) => b.popularity - a.popularity);
    } catch (error) {
      console.error('Failed to search MCP tools:', error);
      throw error;
    }
  }

  /**
   * Get tools for a specific server
   */
  async getServerTools(serverId: string): Promise<MCPTool[]> {
    try {
      // Mock implementation - in production, this would call the server's tool discovery endpoint
      return this.getMockToolsForServer(serverId);
    } catch (error) {
      console.error(`Failed to fetch tools for server ${serverId}:`, error);
      throw error;
    }
  }

  /**
   * Test connection to a specific server
   */
  async testServerConnection(serverId: string): Promise<boolean> {
    try {
      // Mock implementation - in production, this would ping the server
      await new Promise(resolve => setTimeout(resolve, 1000));
      return Math.random() > 0.1; // 90% success rate for demo
    } catch (error) {
      console.error(`Failed to test connection to server ${serverId}:`, error);
      return false;
    }
  }

  /**
   * Register a new MCP server with the gateway
   */
  async registerServer(serverConfig: Partial<MCPServer>): Promise<MCPServer> {
    try {
      const newServer: MCPServer = {
        id: Date.now().toString(),
        name: serverConfig.name || 'Unnamed Server',
        description: serverConfig.description || '',
        url: serverConfig.url || '',
        status: 'disconnected',
        type: serverConfig.type || 'remote',
        transport: serverConfig.transport || 'auto',
        supportedTransports: serverConfig.supportedTransports || ['streamable-http'],
        toolCount: 0,
        categories: serverConfig.categories || [],
        tags: serverConfig.tags || [],
        stars: 0,
        license: serverConfig.license || 'Unknown',
        isPython: serverConfig.isPython || false,
        enabled: serverConfig.enabled !== false,
        authentication: serverConfig.authentication || { type: 'none' },
        agentCompatibility: serverConfig.agentCompatibility,
        lastHealthCheck: new Date()
      };

      this.servers.push(newServer);
      this.saveToStorage();
      return newServer;
    } catch (error) {
      console.error('Failed to register MCP server:', error);
      throw error;
    }
  }

  /**
   * Update an existing MCP server
   */
  async updateServer(serverId: string, updates: Partial<MCPServer>): Promise<MCPServer> {
    try {
      const serverIndex = this.servers.findIndex(s => s.id === serverId);
      if (serverIndex === -1) {
        throw new Error('Server not found');
      }

      this.servers[serverIndex] = { ...this.servers[serverIndex], ...updates };
      this.saveToStorage();
      return this.servers[serverIndex];
    } catch (error) {
      console.error('Failed to update MCP server:', error);
      throw error;
    }
  }

  /**
   * Delete an MCP server
   */
  async deleteServer(serverId: string): Promise<void> {
    try {
      this.servers = this.servers.filter(s => s.id !== serverId);
      this.tools = this.tools.filter(t => t.serverId !== serverId);
      this.saveToStorage();
    } catch (error) {
      console.error('Failed to delete MCP server:', error);
      throw error;
    }
  }

  /**
   * Create a new tool for a server
   */
  async createTool(serverId: string, toolConfig: Partial<MCPTool>): Promise<MCPTool> {
    try {
      const server = this.servers.find(s => s.id === serverId);
      if (!server) {
        throw new Error('Server not found');
      }

      const newTool: MCPTool = {
        id: Date.now().toString(),
        name: toolConfig.name || 'Unnamed Tool',
        description: toolConfig.description || '',
        parameters: toolConfig.parameters || {},
        category: toolConfig.category || 'other',
        serverId,
        serverName: server.name,
        popularity: toolConfig.popularity || 0,
        verified: toolConfig.verified || false,
        agentRecommended: toolConfig.agentRecommended || false,
        usageComplexity: toolConfig.usageComplexity || 'simple',
        requiredPermissions: toolConfig.requiredPermissions || []
      };

      this.tools.push(newTool);
      
      // Update server tool count
      server.toolCount = this.tools.filter(t => t.serverId === serverId).length;
      
      this.saveToStorage();
      return newTool;
    } catch (error) {
      console.error('Failed to create MCP tool:', error);
      throw error;
    }
  }

  /**
   * Update an existing tool
   */
  async updateTool(toolId: string, updates: Partial<MCPTool>): Promise<MCPTool> {
    try {
      const toolIndex = this.tools.findIndex(t => t.id === toolId);
      if (toolIndex === -1) {
        throw new Error('Tool not found');
      }

      this.tools[toolIndex] = { ...this.tools[toolIndex], ...updates };
      this.saveToStorage();
      return this.tools[toolIndex];
    } catch (error) {
      console.error('Failed to update MCP tool:', error);
      throw error;
    }
  }

  /**
   * Delete a tool
   */
  async deleteTool(toolId: string): Promise<void> {
    try {
      const tool = this.tools.find(t => t.id === toolId);
      if (tool) {
        this.tools = this.tools.filter(t => t.id !== toolId);
        
        // Update server tool count
        const server = this.servers.find(s => s.id === tool.serverId);
        if (server) {
          server.toolCount = this.tools.filter(t => t.serverId === tool.serverId).length;
        }
        
        this.saveToStorage();
      }
    } catch (error) {
      console.error('Failed to delete MCP tool:', error);
      throw error;
    }
  }

  /**
   * Create agent-tool bindings for selected tools
   */
  async createAgentToolBindings(agentId: string, selectedTools: { toolId: string; serverId: string; }[]): Promise<AgentToolBinding[]> {
    try {
      const bindings: AgentToolBinding[] = [];

      for (const selection of selectedTools) {
        const tool = await this.getToolById(selection.toolId, selection.serverId);
        if (tool) {
          const binding: AgentToolBinding = {
            agentId,
            toolId: selection.toolId,
            serverId: selection.serverId,
            permissions: tool.requiredPermissions || [],
            enabled: true,
            createdAt: new Date()
          };
          bindings.push(binding);
        }
      }

      // In production, this would save to the gateway registry
      return bindings;
    } catch (error) {
      console.error('Failed to create agent tool bindings:', error);
      throw error;
    }
  }

  /**
   * Get recommended tools for an agent based on its configuration
   */
  async getRecommendedTools(agentConfig: any): Promise<MCPTool[]> {
    try {
      const allTools = await this.getTools();
      
      // Simple recommendation logic - in production, this would use ML/AI
      return allTools
        .filter(tool => tool.agentRecommended)
        .sort((a, b) => b.popularity - a.popularity)
        .slice(0, 10);
    } catch (error) {
      console.error('Failed to get recommended tools:', error);
      throw error;
    }
  }

  // Private helper methods

  private async getToolById(toolId: string, serverId: string): Promise<MCPTool | null> {
    const serverTools = await this.getServerTools(serverId);
    return serverTools.find(tool => tool.id === toolId) || null;
  }

  private filterTools(tools: MCPTool[], filters: ToolSearchFilters): MCPTool[] {
    return tools.filter(tool => {
      if (filters.category && filters.category !== 'all' && tool.category !== filters.category) {
        return false;
      }
      if (filters.verified !== undefined && tool.verified !== filters.verified) {
        return false;
      }
      if (filters.agentRecommended !== undefined && tool.agentRecommended !== filters.agentRecommended) {
        return false;
      }
      if (filters.complexity && tool.usageComplexity !== filters.complexity) {
        return false;
      }
      if (filters.minPopularity && tool.popularity < filters.minPopularity) {
        return false;
      }
      return true;
    });
  }

  private getMockServers(): MCPServer[] {
    return [
      {
        id: 'aws-agentcore-1',
        name: 'AWS AgentCore Gateway',
        description: 'Enterprise AWS services through MCP protocol with Cognito authentication',
        url: 'https://gateway.aws.agentcore.com/mcp',
        status: 'connected',
        type: 'aws',
        transport: 'streamable-http',
        supportedTransports: ['streamable-http', 'sse'],
        toolCount: 15,
        categories: ['aws', 'cloud', 'database', 'storage'],
        tags: ['enterprise', 'verified', 'aws', 'production'],
        stars: 4.8,
        license: 'Apache-2.0',
        isPython: false,
        enabled: true,
        authentication: { type: 'cognito' },
        agentCompatibility: {
          frameworks: ['agentcore', 'strands', 'custom'],
          minVersion: '1.0.0',
          maxConcurrency: 10
        },
        lastHealthCheck: new Date()
      },
      {
        id: 'github-enterprise-1',
        name: 'GitHub Enterprise Tools',
        description: 'GitHub API access with enterprise authentication and advanced workflows',
        url: 'https://mcp.github.enterprise.com/api',
        status: 'connected',
        type: 'remote',
        transport: 'sse',
        supportedTransports: ['sse', 'streamable-http'],
        toolCount: 8,
        categories: ['git', 'collaboration', 'api', 'workflow'],
        tags: ['github', 'enterprise', 'verified', 'collaboration'],
        stars: 4.6,
        license: 'MIT',
        isPython: false,
        enabled: true,
        authentication: { type: 'oauth2' },
        agentCompatibility: {
          frameworks: ['agentcore', 'strands', 'custom'],
          minVersion: '1.2.0',
          maxConcurrency: 5
        },
        lastHealthCheck: new Date()
      },
      {
        id: 'local-dev-tools-1',
        name: 'Local Development Tools',
        description: 'Local development utilities with secure file system access',
        url: 'http://localhost:3001/mcp',
        status: 'connected',
        type: 'local',
        transport: 'auto',
        supportedTransports: ['sse', 'streamable-http'],
        toolCount: 12,
        categories: ['filesystem', 'development', 'utilities', 'testing'],
        tags: ['local', 'development', 'testing', 'utilities'],
        stars: 4.2,
        license: 'MIT',
        isPython: true,
        enabled: true,
        authentication: { type: 'none' },
        agentCompatibility: {
          frameworks: ['agentcore', 'strands', 'custom'],
          minVersion: '0.9.0',
          maxConcurrency: 3
        },
        lastHealthCheck: new Date()
      }
    ];
  }

  private getMockToolsForServer(serverId: string): MCPTool[] {
    const toolsMap: Record<string, MCPTool[]> = {
      'aws-agentcore-1': [
        {
          id: 'aws-s3-upload',
          name: 'S3 File Upload',
          description: 'Upload files to AWS S3 with enterprise security and automatic encryption',
          parameters: { bucket: 'string', key: 'string', file: 'binary', metadata: 'object' },
          category: 'aws',
          serverId: 'aws-agentcore-1',
          serverName: 'AWS AgentCore Gateway',
          popularity: 95,
          verified: true,
          agentRecommended: true,
          usageComplexity: 'simple',
          requiredPermissions: ['s3:PutObject', 's3:PutObjectAcl']
        },
        {
          id: 'aws-dynamodb-query',
          name: 'DynamoDB Query',
          description: 'Query DynamoDB tables with advanced filtering and pagination',
          parameters: { tableName: 'string', keyCondition: 'object', filterExpression: 'string' },
          category: 'aws',
          serverId: 'aws-agentcore-1',
          serverName: 'AWS AgentCore Gateway',
          popularity: 88,
          verified: true,
          agentRecommended: true,
          usageComplexity: 'moderate',
          requiredPermissions: ['dynamodb:Query', 'dynamodb:GetItem']
        },
        {
          id: 'aws-lambda-invoke',
          name: 'Lambda Function Invoke',
          description: 'Invoke AWS Lambda functions with payload and async support',
          parameters: { functionName: 'string', payload: 'object', invocationType: 'string' },
          category: 'aws',
          serverId: 'aws-agentcore-1',
          serverName: 'AWS AgentCore Gateway',
          popularity: 82,
          verified: true,
          agentRecommended: false,
          usageComplexity: 'advanced',
          requiredPermissions: ['lambda:InvokeFunction']
        }
      ],
      'github-enterprise-1': [
        {
          id: 'github-create-pr',
          name: 'Create Pull Request',
          description: 'Create pull requests with automated workflows and review assignments',
          parameters: { repo: 'string', title: 'string', body: 'string', base: 'string', head: 'string' },
          category: 'git',
          serverId: 'github-enterprise-1',
          serverName: 'GitHub Enterprise Tools',
          popularity: 92,
          verified: true,
          agentRecommended: true,
          usageComplexity: 'moderate',
          requiredPermissions: ['repo:write', 'pull_requests:write']
        },
        {
          id: 'github-search-code',
          name: 'Search Code',
          description: 'Search code across repositories with advanced filters and syntax highlighting',
          parameters: { query: 'string', repo: 'string', language: 'string', path: 'string' },
          category: 'git',
          serverId: 'github-enterprise-1',
          serverName: 'GitHub Enterprise Tools',
          popularity: 78,
          verified: true,
          agentRecommended: false,
          usageComplexity: 'simple',
          requiredPermissions: ['repo:read']
        }
      ],
      'local-dev-tools-1': [
        {
          id: 'file-read-secure',
          name: 'Secure File Read',
          description: 'Read local files with permission checks and content validation',
          parameters: { path: 'string', encoding: 'string', maxSize: 'number' },
          category: 'filesystem',
          serverId: 'local-dev-tools-1',
          serverName: 'Local Development Tools',
          popularity: 76,
          verified: false,
          agentRecommended: true,
          usageComplexity: 'simple',
          requiredPermissions: ['file:read']
        },
        {
          id: 'run-tests',
          name: 'Run Test Suite',
          description: 'Execute test suites with coverage reporting and result analysis',
          parameters: { testPath: 'string', framework: 'string', coverage: 'boolean' },
          category: 'development',
          serverId: 'local-dev-tools-1',
          serverName: 'Local Development Tools',
          popularity: 84,
          verified: false,
          agentRecommended: true,
          usageComplexity: 'moderate',
          requiredPermissions: ['exec:test']
        }
      ]
    };

    return toolsMap[serverId] || [];
  }
}

// Export singleton instance
export const mcpGatewayService = new MCPGatewayService();
export default MCPGatewayService;