import assert from "node:assert/strict";
import { dateToPythonOrdinal, normalizePosts, selectPost } from "./worker.mjs";

const posts = normalizePosts({ posts: [
  { message: "A" },
  { message: "B", link: "https://example.com" },
  { message: "C" },
] });
assert.equal(posts.length, 3);
assert.deepEqual(selectPost(posts, { index: 1 }), { message: "B", link: "https://example.com" });
assert.deepEqual(selectPost(posts, { index: -1 }), { message: "C" });
assert.equal(dateToPythonOrdinal(new Date("1970-01-01T00:00:00Z")), 719163);
assert.equal(selectPost(posts, { date: new Date("2026-08-10T00:17:00Z") }).message, posts[dateToPythonOrdinal(new Date("2026-08-10T00:17:00Z")) % posts.length].message);
assert.throws(() => normalizePosts({ posts: [] }), /non-empty/);
assert.throws(() => normalizePosts({ posts: [{ message: "" }] }), /non-empty string/);
console.log("cloudflare worker tests: ok");
