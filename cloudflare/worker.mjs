const DEFAULT_GRAPH_VERSION = "v25.0";
const DEFAULT_POSTS_URL = "https://raw.githubusercontent.com/univcorp2-ctrl/facebook-auto-post/main/posts/posts.json";
const PYTHON_UNIX_EPOCH_ORDINAL = 719163;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export function normalizePosts(data) {
  const rawPosts = Array.isArray(data) ? data : data?.posts;
  if (!Array.isArray(rawPosts) || rawPosts.length === 0) throw new Error("posts file must contain a non-empty list or a non-empty posts array");
  return rawPosts.map((raw, index) => {
    if (!raw || typeof raw !== "object") throw new Error(`posts[${index}] must be an object`);
    const message = typeof raw.message === "string" ? raw.message.trim() : "";
    const link = typeof raw.link === "string" ? raw.link.trim() : "";
    if (!message) throw new Error(`posts[${index}].message must be a non-empty string`);
    return { message, ...(link ? { link } : {}) };
  });
}

export function dateToPythonOrdinal(date) {
  const utcMidnight = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  return Math.floor(utcMidnight / 86400000) + PYTHON_UNIX_EPOCH_ORDINAL;
}

export function selectPost(posts, { date = new Date(), index } = {}) {
  if (!Array.isArray(posts) || posts.length === 0) throw new Error("posts must not be empty");
  const selected = Number.isInteger(index) ? ((index % posts.length) + posts.length) % posts.length : dateToPythonOrdinal(date) % posts.length;
  return posts[selected];
}

async function loadPosts(env) {
  const response = await fetch(env.POSTS_URL || DEFAULT_POSTS_URL, { headers: { "user-agent": "facebook-auto-post-cloudflare-worker" } });
  if (!response.ok) throw new Error(`failed to load posts: HTTP ${response.status}`);
  return normalizePosts(await response.json());
}

async function resolvePost(env, requestBody = {}) {
  if (typeof requestBody.message === "string" && requestBody.message.trim()) {
    const link = typeof requestBody.link === "string" ? requestBody.link.trim() : "";
    return { message: requestBody.message.trim(), ...(link ? { link } : {}) };
  }
  const posts = await loadPosts(env);
  const parsedIndex = requestBody.post_index === undefined || requestBody.post_index === null || requestBody.post_index === "" ? undefined : Number(requestBody.post_index);
  return selectPost(posts, { index: Number.isInteger(parsedIndex) ? parsedIndex : undefined });
}

async function publishToFacebook(env, post) {
  if (!env.FB_PAGE_ID || !env.FB_PAGE_ACCESS_TOKEN) throw new Error("FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be configured as Worker secrets");
  const graphVersion = (env.FB_GRAPH_VERSION || DEFAULT_GRAPH_VERSION).replace(/^\/+|\/+$/g, "");
  const pageId = String(env.FB_PAGE_ID).trim();
  const payload = new URLSearchParams({ access_token: String(env.FB_PAGE_ACCESS_TOKEN).trim(), published: "true", message: post.message });
  if (post.link) payload.set("link", post.link);
  const response = await fetch(`https://graph.facebook.com/${graphVersion}/${encodeURIComponent(pageId)}/feed`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: payload,
  });
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text.slice(0, 500) }; }
  if (!response.ok) {
    const apiMessage = data?.error?.message || `HTTP ${response.status}`;
    const apiCode = data?.error?.code ? ` code=${data.error.code}` : "";
    throw new Error(`Facebook API error${apiCode}: ${apiMessage}`);
  }
  return data;
}

async function runPost(env, requestBody = {}) {
  const post = await resolvePost(env, requestBody);
  if (requestBody.dry_run === true || requestBody.dry_run === "true") return { dry_run: true, post };
  return { published: true, post, result: await publishToFacebook(env, post) };
}

function isAuthorized(request, env) {
  if (!env.CUSTOM_GPT_SHARED_SECRET) return false;
  return (request.headers.get("authorization") || "") === `Bearer ${env.CUSTOM_GPT_SHARED_SECRET}`;
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runPost(env).then((result) => console.log(JSON.stringify({ event: "facebook_scheduled_post", cron: controller.cron, result }))).catch((error) => {
      console.error(JSON.stringify({ event: "facebook_scheduled_post_error", cron: controller.cron, message: error.message }));
      throw error;
    }));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") return jsonResponse({ ok: true, service: "facebook-auto-post", scheduled: "17 0 * * * UTC / 09:17 JST" });
    if (url.pathname !== "/post") return jsonResponse({ error: "not_found" }, 404);
    if (request.method !== "POST") return jsonResponse({ error: "method_not_allowed" }, 405);
    if (!isAuthorized(request, env)) return jsonResponse({ error: "unauthorized" }, 401);
    try {
      const body = await request.json().catch(() => ({}));
      return jsonResponse(await runPost(env, body));
    } catch (error) {
      console.error(JSON.stringify({ event: "facebook_manual_post_error", message: error.message }));
      return jsonResponse({ error: "post_failed", message: error.message }, 502);
    }
  },
};
