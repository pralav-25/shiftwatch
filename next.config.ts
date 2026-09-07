import type { NextConfig } from 'next';
const nextConfig: NextConfig = {
  output: 'export',
  // This single-route viewer is mounted by Pages at /shiftwatch. Prefix assets
  // without changing the prerender route: Vinext beta.5 skips / with basePath.
  ...(process.env.GITHUB_PAGES === 'true'
    ? { assetPrefix: 'https://pralav-25.github.io/shiftwatch' }
    : {}),
};
export default nextConfig;
