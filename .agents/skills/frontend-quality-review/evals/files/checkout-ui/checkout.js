const form = document.querySelector("#checkout-form");
const payButton = document.querySelector("#pay-button");
const status = document.querySelector("#checkout-status");
const errorSummary = document.querySelector("#error-summary");
const paymentClient = window.paymentClient;

form.addEventListener("input", () => {
  payButton.disabled = !form.checkValidity();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.classList.add("loading");
  status.textContent = "Processing payment...";
  payButton.disabled = true;

  try {
    await paymentClient.charge(new FormData(form));
    status.classList.remove("loading");
    status.textContent = "Payment complete. Your receipt is on its way.";
    payButton.disabled = false;
  } catch (error) {
    status.classList.remove("loading");
    status.textContent = "We could not complete the payment. Please try again.";
    payButton.disabled = false;
  }
});

form.addEventListener("invalid", () => {
  errorSummary.hidden = false;
  errorSummary.textContent = "Please check the highlighted fields.";
}, true);
