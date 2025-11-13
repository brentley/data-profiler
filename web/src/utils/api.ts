// API Client for VQ8 Data Profiler Backend
import type {
  CreateRunRequest,
  CreateRunResponse,
  RunStatus,
  Profile,
  CandidateKeysResponse,
  ConfirmKeysRequest,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(
    message: string,
    status: number,
    data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.message || `HTTP ${response.status}`,
        response.status,
        errorData
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

export const api = {
  // Health check
  async healthCheck(): Promise<{ status: string }> {
    return fetchApi('/healthz');
  },

  // Create a new profiling run
  async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
    return fetchApi('/runs', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Upload file for a run
  async uploadFile(runId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE_URL}/runs/${runId}/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.message || `Upload failed: HTTP ${response.status}`,
        response.status,
        errorData
      );
    }
  },

  // Get run status
  async getRunStatus(runId: string): Promise<RunStatus> {
    return fetchApi(`/runs/${runId}/status`);
  },

  // Get full profile
  async getProfile(runId: string): Promise<Profile> {
    return fetchApi(`/runs/${runId}/profile`);
  },

  // Get candidate keys suggestions
  async getCandidateKeys(runId: string): Promise<CandidateKeysResponse> {
    return fetchApi(`/runs/${runId}/candidate-keys`);
  },

  // Confirm keys for duplicate check
  async confirmKeys(runId: string, request: ConfirmKeysRequest): Promise<void> {
    return fetchApi(`/runs/${runId}/confirm-keys`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Download URLs
  getMetricsCsvUrl(runId: string): string {
    return `${API_BASE_URL}/runs/${runId}/metrics.csv`;
  },

  getReportHtmlUrl(runId: string): string {
    return `${API_BASE_URL}/runs/${runId}/report.html`;
  },

  getProfileJsonUrl(runId: string): string {
    return `${API_BASE_URL}/runs/${runId}/profile`;
  },
};

export { ApiError };
