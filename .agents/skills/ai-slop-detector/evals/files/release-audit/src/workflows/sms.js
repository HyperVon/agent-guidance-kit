export async function sendSms(transport, message) {
  try {
    return await transport.send({ channel: "sms", ...message });
  } catch (error) {
    return { ok: false, error: "notification failed" };
  }
}
