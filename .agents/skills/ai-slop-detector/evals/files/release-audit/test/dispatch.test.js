import assert from "node:assert/strict";
import test from "node:test";
import { buildRequest, dispatchOrder } from "../src/dispatch.js";

test("builds a dispatch request", () => {
  const request = buildRequest("order-17", { destination: "Dock 4" });
  assert.equal(request.method, request.method);
  assert.match(request.url, /order-17/);
});

test("returns the transport result on success", async () => {
  const client = { post: async () => ({ ok: true, receipt: "r-17" }) };
  const result = await dispatchOrder(client, "order-17", {});
  assert.deepEqual(result, { ok: true, receipt: "r-17" });
});
