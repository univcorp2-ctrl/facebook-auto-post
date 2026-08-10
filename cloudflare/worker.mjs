const DEFAULT_GRAPH_VERSION = "v25.0";
const DEFAULT_POSTS_URL = "https://raw.githubusercontent.com/univcorp2-ctrl/facebook-auto-post/main/posts/posts.json";
const DEFAULT_AI_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8";
const PYTHON_UNIX_EPOCH_ORDINAL = 719163;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function enabled(value, defaultValue = true) {
  if (value === undefined || value === null || value === "") return defaultValue;
  return !["0", "false", "off", "no"].includes(String(value).trim().toLowerCase());
}

export function normalizePosts(data) {
  const rawPosts = Array.isArray(data) ? data : data?.posts;
  if (!Array.isArray(rawPosts) || rawPosts.length === 0) {
    throw new Error("posts file must contain a non-empty list or a non-empty posts array");
  }
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
  const selected = Number.isInteger(index)
    ? ((index % posts.length) + posts.length) % posts.length
    : dateToPythonOrdinal(date) % posts.length;
  return posts[selected];
}

export function cleanGeneratedMessage(value) {
  let text = String(value ?? "").trim();
  text = text.replace(/^```(?:text|markdown|md)?\s*/i, "").replace(/\s*```$/i, "").trim();
  text = text.replace(/^(?:投稿文|本文|Facebook投稿)\s*[:：]\s*/i, "").trim();
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("「") && text.endsWith("」"))) {
    text = text.slice(1, -1).trim();
  }
  text = text.replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  if (text.length < 20) throw new Error("Workers AI returned a message that is too short");
  if (text.length > 1200) throw new Error("Workers AI returned a message that is too long");
  return text;
}

export function extractAIText(result) {
  if (typeof result === "string") return result;
  if (typeof result?.response === "string") return result.response;
  if (typeof result?.result === "string") return result.result;
  if (typeof result?.output_text === "string") return result.output_text;
  if (typeof result?.choices?.[0]?.message?.content === "string") return result.choices[0].message.content;
  throw new Error("Workers AI response did not contain generated text");
}

async function loadPosts(env) {
  const response = await fetch(env.POSTS_URL || DEFAULT_POSTS_URL, {
    headers: { "user-agent": "facebook-auto-post-cloudflare-worker" },
  });
  if (!response.ok) throw new Error(`failed to load posts: HTTP ${response.status}`);
  return normalizePosts(await response.json());
}

function selectedIndex(requestBody) {
  if (requestBody.post_index === undefined || requestBody.post_index === null || requestBody.post_index === "") return undefined;
  const parsed = Number(requestBody.post_index);
  return Number.isInteger(parsed) ? parsed : undefined;
}

function aiPrompt(seedPost, env, requestBody) {
  const additional = String(requestBody.ai_instruction || env.AI_POST_INSTRUCTION || "").trim();
  const system = [
    "あなたは日本語のFacebook投稿を作る編集者です。",
    "元投稿に書かれている事実・数値・固有名詞だけを使い、読みやすく自然な投稿文に書き換えてください。",
    "元投稿にない実績、価格、人物、会社情報、保証、投資成果などを新しく作らないでください。",
    "120〜320文字程度を目安にし、営業色を強くしすぎず、絵文字は0〜2個、ハッシュタグは最大3個にしてください。",
    "Markdownの見出し、コードフェンス、前置き、解説は不要です。投稿本文だけを返してください。",
    additional ? `追加指示: ${additional}` : "",
  ].filter(Boolean).join("\n");
  const user = [
    "次の元投稿を、意味と重要な情報を保ったまま別表現のFacebook投稿にしてください。",
    "",
    `元投稿:\n${seedPost.message}`,
    seedPost.link ? `\nリンク: ${seedPost.link}\nリンクは本文に無理に埋め込まず、投稿側のリンク欄で扱います。` : "",
  ].filter(Boolean).join("\n");
  return { system, user };
}

export async function generatePostWithAI(env, seedPost, requestBody = {}) {
  if (!env.AI || typeof env.AI.run !== "function") throw new Error("Workers AI binding AI is not configured");
  const model = String(requestBody.ai_model || env.AI_MODEL || DEFAULT_AI_MODEL).trim();
  const { system, user } = aiPrompt(seedPost, env, requestBody);
  const result = await env.AI.run(model, {
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    max_completion_tokens: 420,
    temperature: 0.72,
  });
  const message = cleanGeneratedMessage(extractAIText(result));
  return {
    message,
    ...(seedPost.link ? { link: seedPost.link } : {}),
    generated_by_ai: true,
    ai_model: model,
  };
}

async function resolvePost(env, requestBody = {}) {
  if (typeof requestBody.message === "string" && requestBody.message.trim()) {
    const link = typeof requestBody.link === "string" ? requestBody.link.trim() : "";
    return { message: requestBody.message.trim(), ...(link ? { link } : {}), generated_by_ai: false, source: "manual" };
  }
  const posts = await loadPosts(env);
  const seedPost = selectPost(posts, { index: selectedIndex(requestBody) });
  const useAI = enabled(requestBody.use_ai, enabled(env.AI_ENABLED, true));
  if (!useAI) return { ...seedPost, generated_by_ai: false, source: "posts_json" };
  try {
    return await generatePostWithAI(env, seedPost, requestBody);
  } catch (error) {
    if (!enabled(env.AI_FALLBACK, true)) throw error;
    console.error(JSON.stringify({ event: "workers_ai_fallback", message: error.message }));
    return { ...seedPost, generated_by_ai: false, source: "posts_json_fallback", ai_fallback: true, ai_error: error.message };
  }
}

async function publishToFacebook(env, post) {
  if (!env.FB_PAGE_ID || !env.FB_PAGE_ACCESS_TOKEN) {
    throw new Error("FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be configured as Worker secrets");
  }
  const graphVersion = (env.FB_GRAPH_VERSION || DEFAULT_GRAPH_VERSION).replace(/^\/+|\/+$/g, "");
  const pageId = String(env.FB_PAGE_ID).trim();
  const payload = new URLSearchParams({
    access_token: String(env.FB_PAGE_ACCESS_TOKEN).trim(),
    published: "true",
    message: post.message,
  });
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
  const dryRun = requestBody.dry_run === true || requestBody.dry_run === "true";
  if (dryRun) return { dry_run: true, post };
  return { published: true, post, result: await publishToFacebook(env, post) };
}

function isAuthorized(request, env) {
  if (!env.CUSTOM_GPT_SHARED_SECRET) return false;
  return (request.headers.get("authorization") || "") === `Bearer ${env.CUSTOM_GPT_SHARED_SECRET}`;
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(
      runPost(env)
        .then((result) => console.log(JSON.stringify({ event: "facebook_scheduled_post", cron: controller.cron, result })))
        .catch((error) => {
          console.error(JSON.stringify({ event: "facebook_scheduled_post_error", cron: controller.cron, message: error.message }));
          throw error;
        }),
    );
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return jsonResponse({
        ok: true,
        service: "facebook-auto-post",
        scheduled: "17 0 * * * UTC / 09:17 JST",
        workers_ai: {
          enabled: enabled(env.AI_ENABLED, true),
          model: env.AI_MODEL || DEFAULT_AI_MODEL,
          fallback_to_posts_json: enabled(env.AI_FALLBACK, true),
        },
      });
    }
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
