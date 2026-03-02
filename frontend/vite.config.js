import { defineConfig, loadEnv } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import fs from 'node:fs';
import os from 'node:os';

function parseLittleEndianHexIp(hex) {
  if (!hex || hex.length !== 8) {
    return null;
  }
  const parts = hex.match(/../g);
  if (!parts || parts.length !== 4) {
    return null;
  }
  return parts.reverse().map((v) => String(parseInt(v, 16))).join('.');
}

function detectWslHostFromRoute() {
  try {
    const content = fs.readFileSync('/proc/net/route', 'utf-8');
    const lines = content
      .split('\n')
      .map((v) => v.trim())
      .filter(Boolean)
      .slice(1);

    for (const line of lines) {
      const cols = line.split(/\s+/);
      if (cols.length < 3) {
        continue;
      }
      const destination = cols[1];
      const gateway = cols[2];
      if (destination !== '00000000' || gateway === '00000000') {
        continue;
      }
      const ip = parseLittleEndianHexIp(gateway);
      if (ip) {
        return ip;
      }
    }
    return null;
  } catch {
    return null;
  }
}

function detectNameServer() {
  try {
    const content = fs.readFileSync('/etc/resolv.conf', 'utf-8');
    const line = content
      .split('\n')
      .map((v) => v.trim())
      .find((v) => v.toLowerCase().startsWith('nameserver '));
    if (!line) {
      return null;
    }
    const ip = line.split(/\s+/)[1];
    return ip || null;
  } catch {
    return null;
  }
}

function detectProxyTarget() {
  const envTarget = process.env.VITE_PROXY_TARGET;
  if (envTarget && envTarget.trim()) {
    return envTarget.trim();
  }

  const release = os.release().toLowerCase();
  const isWsl = process.platform === 'linux' && (release.includes('microsoft') || release.includes('wsl'));
  if (!isWsl) {
    return 'http://localhost:8000';
  }

  const routeHostIp = detectWslHostFromRoute();
  if (routeHostIp && !routeHostIp.startsWith('10.255.')) {
    return `http://${routeHostIp}:8000`;
  }

  const dnsIp = detectNameServer();
  if (dnsIp && !dnsIp.startsWith('10.255.')) {
    return `http://${dnsIp}:8000`;
  }

  return 'http://127.0.0.1:8000';
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.VITE_PROXY_TARGET || detectProxyTarget();
  console.log(`[vite] proxy target: ${proxyTarget}`);

  return {
    plugins: [svelte()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/health': {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
