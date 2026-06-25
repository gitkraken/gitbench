import assert from "node:assert/strict";
import test from "node:test";

import emailSignupsHandler, {
  buildHubSpotPayload,
} from "../api/email-signups.ts";

async function callHandler({ method = "POST", body } = {}) {
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
  await emailSignupsHandler({ method, body }, res);
  return {
    statusCode: res.statusCode,
    headers: res.headers,
    body: JSON.parse(res.body),
  };
}

test("buildHubSpotPayload maps email to the HubSpot form field", () => {
  assert.deepEqual(buildHubSpotPayload({ email: "test@example.com" }), {
    fields: [{ name: "0-1/email", value: "test@example.com" }],
  });
});

test("email signup endpoint submits a valid email to HubSpot", async () => {
  const previousFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedInit;

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedInit = init;
    return {
      ok: true,
      status: 200,
      statusText: "OK",
    };
  };

  try {
    const response = await callHandler({
      body: { email: " test@example.com " },
    });

    assert.equal(response.statusCode, 200);
    assert.deepEqual(response.body, {
      ok: true,
      email: "test@example.com",
    });
    assert.equal(
      requestedUrl,
      "https://api.hsforms.com/submissions/v3/integration/submit/544893/22143c4c-3889-47a0-9ffa-b22deb639ba7"
    );
    assert.equal(requestedInit.method, "POST");
    assert.deepEqual(requestedInit.headers, {
      "content-type": "application/json",
    });
    assert.deepEqual(JSON.parse(requestedInit.body), {
      fields: [{ name: "0-1/email", value: "test@example.com" }],
    });
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("email signup endpoint returns a safe error when HubSpot rejects the submission", async () => {
  const previousFetch = globalThis.fetch;
  const previousConsoleError = console.error;

  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    statusText: "Internal Server Error",
  });
  console.error = () => {};

  try {
    const response = await callHandler({
      body: { email: "test@example.com" },
    });

    assert.equal(response.statusCode, 502);
    assert.deepEqual(response.body, {
      ok: false,
      error:
        "We could not submit your email right now. Please try again shortly.",
    });
  } finally {
    globalThis.fetch = previousFetch;
    console.error = previousConsoleError;
  }
});

test("email signup endpoint rejects invalid email before calling HubSpot", async () => {
  const previousFetch = globalThis.fetch;
  let fetchCalled = false;

  globalThis.fetch = async () => {
    fetchCalled = true;
    return { ok: true };
  };

  try {
    const response = await callHandler({
      body: { email: "not-an-email" },
    });

    assert.equal(response.statusCode, 400);
    assert.deepEqual(response.body, {
      ok: false,
      error: "Please enter a valid email address.",
    });
    assert.equal(fetchCalled, false);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("email signup endpoint is post-only", async () => {
  const response = await callHandler({
    method: "GET",
  });

  assert.equal(response.statusCode, 405);
  assert.equal(response.headers.allow, "POST");
  assert.deepEqual(response.body, {
    ok: false,
    error: "method_not_allowed",
  });
});
