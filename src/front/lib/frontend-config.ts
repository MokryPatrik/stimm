/**
 * Simplified Frontend Environment Configuration
 * Handles SSR vs Client-Side environment differences
 */

// Environment detection
const detectServerEnvironment = () => {
  // Check if we're running on server-side (SSR)
  if (typeof window !== 'undefined') {
    return {
      isServerSide: false,
      hostname: 'localhost'
    }
  }
  
  // Server-side environment detection
  try {
    const fs = require('fs')
    
    // Check for .dockerenv file
    if (fs.existsSync('/.dockerenv')) {
      return {
        isServerSide: true,
        hostname: 'voicebot-app'
      }
    }
    
    // Check for Docker environment variables
    const dockerEnvVars = ['DOCKER_CONTAINER', 'COMPOSE_SERVICE_NAME', 'DOCKER_SERVICE_NAME']
    
    for (const envVar of dockerEnvVars) {
      if (process.env[envVar]) {
        return {
          isServerSide: true,
          hostname: 'voicebot-app'
        }
      }
    }
    
    // Check cgroup
    if (fs.existsSync('/proc/1/cgroup')) {
      const cgroupContent = fs.readFileSync('/proc/1/cgroup', 'utf8')
      const dockerPatterns = ['docker', 'lxc', 'kubepods', 'containerd']
      
      for (const pattern of dockerPatterns) {
        if (cgroupContent.includes(pattern)) {
          return {
            isServerSide: true,
            hostname: 'voicebot-app'
          }
        }
      }
    }
    
  } catch (error) {
    console.warn('Could not detect server environment:', error)
  }
  
  return {
    isServerSide: true,
    hostname: 'localhost'
  }
}

// Main configuration function
export const getFrontendConfig = () => {
  const serverEnv = detectServerEnvironment()
  
  // For SSR: use environment-aware URLs
  // For Client: always use localhost
  const isClientSide = typeof window !== 'undefined'
  const backendHost = isClientSide ? 'localhost' : serverEnv.hostname
  
  return {
    // Backend API URLs
    backend: {
      apiUrl: `http://${backendHost}:8001`,
      wsUrl: `ws://${backendHost}:8001`,
    },
    
    // Always use localhost for browser connections
    browser: {
      voicebotApiUrl: 'http://localhost:8001',
      liveKitWsUrl: 'ws://localhost:7880',
    },
    
    // Environment info
    environment: {
      isServerSide: serverEnv.isServerSide,
      hostname: backendHost,
      type: serverEnv.hostname === 'localhost' ? 'local' : 'docker'
    }
  }
}

// Singleton instance
let config: ReturnType<typeof getFrontendConfig> | null = null

export const getConfig = () => {
  if (!config) {
    config = getFrontendConfig()
  }
  return config
}

// Environment-aware API client
export class FrontendApiClient {
  private config: ReturnType<typeof getConfig>
  
  constructor() {
    this.config = getConfig()
  }
  
  /**
   * Make API calls with environment-aware URL handling
   */
  async apiCall(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const isClientSide = typeof window !== 'undefined'
    
    // For client-side calls, always use localhost
    // For SSR calls, use environment-aware URLs
    const baseUrl = isClientSide 
      ? this.config.browser.voicebotApiUrl
      : this.config.backend.apiUrl
    
    const url = `${baseUrl}${endpoint}`
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    
    return fetch(url, {
      ...options,
      headers,
    })
  }
  
  /**
   * Get LiveKit WebSocket URL (always localhost for browser)
   */
  getLiveKitUrl(): string {
    return this.config.browser.liveKitWsUrl
  }
  
  /**
   * Get environment information
   */
  getEnvironment() {
    return this.config.environment
  }
}

// Export singleton
export const apiClient = new FrontendApiClient()