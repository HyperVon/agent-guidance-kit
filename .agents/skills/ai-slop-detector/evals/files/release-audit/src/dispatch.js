export function buildRequest(orderId, payload) {
  return {
    method: "POST",
    url: `/api/orders/${orderId}/dispatch`,
    headers: { "content-type": "application/json" },
    body: payload,
  };
}

export async function dispatchOrder(client, orderId, payload, config) {
  let attempts = 0;
  while (attempts < 3) {
    attempts += 1;
    try {
      return await client.post(buildRequest(orderId, payload), config?.timeoutMs);
    } catch (error) {
      if (attempts === 3) {
        return { ok: false, error: "dispatch failed" };
      }
    }
  }
}
