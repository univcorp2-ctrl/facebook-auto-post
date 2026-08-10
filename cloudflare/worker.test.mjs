import assert from "node:assert/strict";
import { cleanGeneratedMessage, dateToPythonOrdinal, extractAIText, generatePostWithAI, normalizePosts, selectPost } from "./worker.mjs";

const posts = normalizePosts({ posts: [
  { message: "A message long enough for a seed post." },
  { message: "B message long enough for a seed post.", link: "https://example.com" },
  { message: "C message long enough for a seed post." },
] });
assert.equal(posts.length, 3);
assert.deepEqual(selectPost(posts, { index: 1 }), { message: "B message long enough for a seed post.", link: "https://example.com" });
assert.deepEqual(selectPost(posts, { index: -1 }), { message: "C message long enough for a seed post." });
assert.equal(dateToPythonOrdinal(new Date("1970-01-01T00:00:00Z")), 719163);
assert.throws(() => normalizePosts({ posts: [] }), /non-empty/);
assert.throws(() => normalizePosts({ posts: [{ message: "" }] }), /non-empty string/);
assert.equal(cleanGeneratedMessage("投稿文：これは十分な長さのテスト投稿本文です。読みやすく整えました。"), "これは十分な長さのテスト投稿本文です。読みやすく整えました。");
assert.equal(extractAIText({ response: "generated" }), "generated");
assert.throws(() => cleanGeneratedMessage("短い"), /too short/);
let calledModel = null;
const env = {
  AI_MODEL: "@cf/qwen/qwen3-30b-a3b-fp8",
  AI: {
    async run(model, input) {
      calledModel = model;
      assert.equal(input.messages[0].role, "system");
      assert.match(input.messages[1].content, /元投稿/);
      return { response: "不動産投資の情報を、元の内容を保ちながら読みやすく整理しました。判断材料を確認しながら、無理のない運用を心がけましょう。#不動産投資" };
    },
  },
};
const generated = await generatePostWithAI(env, { message: "不動産投資の元投稿です。十分な情報があります。", link: "https://example.com" });
assert.equal(calledModel, "@cf/qwen/qwen3-30b-a3b-fp8");
assert.equal(generated.generated_by_ai, true);
assert.equal(generated.link, "https://example.com");
assert.match(generated.message, /不動産投資/);
console.log("cloudflare worker tests: ok");
