import { apiClient } from '../apiClient';

class OllamaService {
  async getModels() {
    try {
      const response = await apiClient.getOllamaModels();
      return response.models || [];
    } catch (error) {
      console.error('Failed to get Ollama models:', error);
      throw error;
    }
  }

  async listModels() {
    try {
      // Use direct Ollama API to get models
      const response = await fetch('http://localhost:11434/api/tags');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.models || [];
    } catch (error) {
      console.error('Failed to list Ollama models:', error);
      throw error;
    }
  }

  async executeCommand(command: string) {
    try {
      const response = await apiClient.executeOllamaCommand(command);
      return response;
    } catch (error) {
      console.error('Failed to execute Ollama command:', error);
      throw error;
    }
  }

  async getStatus() {
    try {
      const response = await apiClient.getOllamaStatus();
      return response;
    } catch (error) {
      console.error('Failed to get Ollama status:', error);
      throw error;
    }
  }

  async generateResponse(model: string, prompt: string, options: any = {}) {
    try {
      // Use the direct Ollama API for generation
      const response = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: model,
          prompt: prompt,
          stream: false,
          options: {
            temperature: options.temperature || 0.7,
            num_predict: options.max_tokens || 1000,
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      return {
        status: 'success',
        response: data.response,
        eval_count: data.eval_count || 0,
        eval_duration: data.eval_duration || 0
      };
    } catch (error) {
      console.error('Failed to generate response:', error);
      return {
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
        response: '',
        eval_count: 0
      };
    }
  }
}

export const ollamaService = new OllamaService();
export default ollamaService;
