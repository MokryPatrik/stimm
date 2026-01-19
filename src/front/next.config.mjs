/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // Make environment info available to the frontend
    NEXT_PUBLIC_ENVIRONMENT_TYPE:
      process.env.NODE_ENV === 'development' ? 'local' : 'docker',
    // These will be overridden by actual env vars if set
    // In production, the .env.prod file sets the correct hostnames
  },
  experimental: {
    serverComponentsExternalPackages: [],
  },
  // Configure for dual-mode development
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
