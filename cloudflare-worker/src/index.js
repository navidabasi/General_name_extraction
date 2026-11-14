import rules from "./extraction_rules.json";

export default {
  async fetch(request) {
    const headers = {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
    };
    if (request.method !== "GET") {
      return new Response(JSON.stringify({ error: "Method not allowed" }),
        { status: 405, headers: { ...headers, allow: "GET" } });
    }
    const path = new URL(request.url).pathname.replace(/\/+$/, "") || "/";
    if (path === "/rules/extraction") {
      return new Response(JSON.stringify(rules), { headers });
    }
    if (path === "/" || path === "/config") {
      return new Response(JSON.stringify({
        app: "name-extractor",
        revision: rules.revision,
        ventrata_rules_url: "https://crown-report-config.navid-kill-policy.workers.dev/rules/extraction",
        extraction_rules_url: `${new URL(request.url).origin}/rules/extraction`,
      }), { headers });
    }
    return new Response(JSON.stringify({ error: "Not found" }), { status: 404, headers });
  },
};
