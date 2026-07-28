import { afterEach, describe, expect, it, vi } from "vitest";

import { apiPost } from "./client";

describe("apiPost", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses structured API error details when present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 409,
            json: async () => ({
              detail: "An inference request already uses this request id.",
            }),
          }) as Response,
      ),
    );

    await expect(apiPost("/api/v1/example", {}, {})).rejects.toThrow(
      "An inference request already uses this request id.",
    );
  });

  it("falls back to the response status when no structured detail exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 500,
            json: async () => ({}),
          }) as Response,
      ),
    );

    await expect(apiPost("/api/v1/example", {}, {})).rejects.toThrow(
      "ForgeML API request failed with 500",
    );
  });
});
