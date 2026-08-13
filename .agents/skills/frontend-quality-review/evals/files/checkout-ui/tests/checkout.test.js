const fs = require("node:fs");

const page = fs.readFileSync("checkout.html", "utf8");
const script = fs.readFileSync("checkout.js", "utf8");

if (!page.includes("Complete your purchase")) {
  throw new Error("checkout heading is missing");
}

if (!page.includes("Pay $84.00")) {
  throw new Error("checkout total is missing");
}

if (!script.includes("Payment complete")) {
  throw new Error("success state is missing");
}

console.log("checkout smoke test passed");
