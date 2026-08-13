export function loadConfig(env = process.env) {
  return {
    retryLimit: Number(env.DISPATCH_RETRY_LIMIT ?? 3),
    timeoutMs: Number(env.DISPATCH_TIMEOUT_MS ?? 5000),
  };
}
