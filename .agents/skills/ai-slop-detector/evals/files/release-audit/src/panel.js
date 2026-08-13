import { dispatchOrder } from "./dispatch.js";

const form = document.querySelector("#dispatch-form");
const status = document.querySelector("#dispatch-status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Sending…";
  const data = Object.fromEntries(new FormData(form));
  const result = await dispatchOrder(window.dispatchClient, data.orderId, data);
  status.textContent = result.ok === false ? "Dispatch failed" : "Dispatch sent";
});
