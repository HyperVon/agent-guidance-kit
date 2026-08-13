export async function sendEmail(transport, message) {
  try {
    return await transport.send({ channel: "email", ...message });
  } catch (error) {
    return { ok: false, error: "notification failed" };
  }
}
