const unavailable = (detail) =>
  Response.json({ detail }, { status: 503, headers: { "Cache-Control": "no-store" } });

export async function onRequestPost({ request, env }) {
  let gateway;
  try {
    gateway = new URL(env.GATEWAY_ORIGIN);
    if (
      gateway.protocol !== "https:" ||
      gateway.username ||
      gateway.password ||
      gateway.pathname !== "/" ||
      gateway.search ||
      gateway.hash
    ) {
      return unavailable("Analysis gateway is not configured.");
    }
  } catch {
    return unavailable("Analysis gateway is not configured.");
  }

  try {
    const response = await fetch(new URL("/v1/analyze", gateway), {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("Content-Type") ?? "application/json",
        Accept: "application/json",
      },
      body: request.body,
      redirect: "manual",
    });

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return unavailable("Analysis gateway is unavailable.");
  }
}
