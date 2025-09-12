/**
 * Ollama Service for local AI model integration
 * Provides communication with Ollama API
 */

export interface OllamaModel {
  name: string;
  size: number;
  digest: string;
  modified_at: string;
}

export interface OllamaResponse {
  status: 'success' | 'error';
  response?: string;
  message?: string;
  eval_count?: number;
  eval_duration?: number;
  total_duration?: number;
}

export interface OllamaGenerateOptions {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
  system?: string;
}

export class OllamaService {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:11434') {
    this.baseUrl = baseUrl;
  }

  async getStatus(): Promise<{ status: string; models?: OllamaModel[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`);
      if (response.ok) {
        const data = await response.json();
        return {
          status: 'running',
          models: data.models || []
        };
      }
      return { status: 'error' };
    } catch (error) {
      return { status: 'not_running' };
    }
  }

  async listModels(): Promise<OllamaModel[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`);
      if (response.ok) {
        const data = await response.json();
        return data.models || [];
      }
      return [];
    } catch (error) {
      console.error('Failed to list models:', error);
      return [];
    }
  } 
 async generateResponse(
    model: string,
    prompt: string,
    options?: OllamaGenerateOptions
  ): Promise<OllamaResponse>;
  async generateResponse(params: {
    model: string;
    prompt: string;
    options?: OllamaGenerateOptions;
  }): Promise<OllamaResponse>;
  async generateResponse(
    modelOrParams: string | { model: string; prompt: string; options?: OllamaGenerateOptions },
    prompt?: string,
    options?: OllamaGenerateOptions
  ): Promise<OllamaResponse> {
    try {
      let model: string;
      let actualPrompt: string;
      let actualOptions: OllamaGenerateOptions;

      if (typeof modelOrParams === 'string') {
        model = modelOrParams;
        actualPrompt = prompt!;
        actualOptions = options || {};
      } else {
        model = modelOrParams.model;
        actualPrompt = modelOrParams.prompt;
        actualOptions = modelOrParams.options || {};
      }

      const requestBody = {
        model,
        prompt: actualPrompt,
        stream: false,
        options: {
          temperature: actualOptions.temperature || 0.7,
          num_predict: actualOptions.max_tokens || 1000,
          top_p: actualOptions.top_p || 0.9,
          top_k: actualOptions.top_k || 40
        }
      };

      if (actualOptions.system) {
        (requestBody as any).system = actualOptions.system;
      }

      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (response.ok) {
        const data = await response.json();
        return {
          status: 'success',
          response: data.response,
          eval_count: data.eval_count,
          eval_duration: data.eval_duration,
          total_duration: data.total_duration
        };
      } else {
        const errorData = await response.json();
        return {
          status: 'error',
          message: errorData.error || 'Failed to generate response'
        };
      }
    } catch (error) {
      return {
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async pullModel(modelName: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/pull`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: modelName }),
      });

      if (response.ok) {
        return { success: true, message: `Model ${modelName} pulled successfully` };
      } else {
        const errorData = await response.json();
        return { success: false, message: errorData.error || 'Failed to pull model' };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async deleteModel(modelName: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/delete`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: modelName }),
      });

      if (response.ok) {
        return { success: true, message: `Model ${modelName} deleted successfully` };
      } else {
        const errorData = await response.json();
        return { success: false, message: errorData.error || 'Failed to delete model' };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}

// Global instance
export const ollamaService = new OllamaService();