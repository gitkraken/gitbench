import assert from "node:assert/strict";
import test from "node:test";

import emailSignupsHandler from "../api/email-signups.ts";

function callHandler({ method = "POST", body } = {}) {
  const res = {
    statusCode: null,
    headers: {},
    body: "",
    status(code) {
      this.statusCode = code;
      return this;
    },
    setHeader(key, value) {
      this.headers[key.toLowerCase()] = value;
      return this;
    },
    end(payload) {
      this.body = payload;
    },
  };
  emailSignupsHandler({ method, body }, res);
  return {
    statusCode: res.statusCode,
    headers: res.headers,
    body: JSON.parse(res.body),
  };
}

test("email signup endpoint accepts a valid email", () => {
  const response = callHandler({
    body: { email: " test@example.com " },
  });

  assert.equal(response.statusCode, 202);
  assert.deepEqual(response.body, {
    ok: true,
    email: "test@example.com",
  });
});

test("email signup endpoint rejects invalid email", () => {
  const response = callHandler({
    body: { email: "not-an-email" },
  });

  assert.equal(response.statusCode, 400);
  assert.deepEqual(response.body, {
    ok: false,
    error: "invalid_email",
  });
});

test("email signup endpoint is post-only", () => {
  const response = callHandler({
    method: "GET",
  });

  assert.equal(response.statusCode, 405);
  assert.equal(response.headers.allow, "POST");
  assert.deepEqual(response.body, {
    ok: false,
    error: "method_not_allowed",
  });
});
