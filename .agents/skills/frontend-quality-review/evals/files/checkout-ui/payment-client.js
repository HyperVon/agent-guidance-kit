window.paymentClient = {
  charge(formData) {
    const outcome = new URLSearchParams(window.location.search).get("outcome");
    return new Promise((resolve, reject) => {
      window.setTimeout(() => {
        if (outcome === "declined") {
          reject(new Error("declined"));
          return;
        }
        resolve({ receiptId: "demo-receipt-1007" });
      }, 900);
    });
  }
};
