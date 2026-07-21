export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  console.log("Incoming request:", body);

  const scriptResponse = await agentRequest("/webhook/fathom/script", {
    method: "POST",
    body: body.transcript,
    headers: {
      "Content-Type": "text/plain",
      Accept: "application/json",
    },
  });

  console.log("Script response:", scriptResponse);

  const fathomResponse = await agentRequest("/webhook/fathom", {
    method: "POST",
    body: scriptResponse,
    headers: {
      Accept: "application/json",
    },
  });

  console.log("Fathom response:", fathomResponse);

  return fathomResponse;
});
