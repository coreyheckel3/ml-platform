import { describe, expect, it } from "vitest";

import { navigationItems } from "./navigation";
import { appRoutes, preloadRoute } from "./routes";

describe("appRoutes", () => {
  it("keeps every navigation item backed by a preloaded lazy route", () => {
    const routesByPath = new Map(appRoutes.map((route) => [route.path, route]));

    for (const item of navigationItems) {
      const route = routesByPath.get(item.path);

      expect(route).toBeDefined();
      expect(route?.preload).toEqual(expect.any(Function));
    }
  });

  it("keeps the wildcard redirect outside the navigation contract", () => {
    expect(appRoutes.at(-1)?.path).toBe("*");
    expect(appRoutes.at(-1)?.preload).toBeUndefined();
  });

  it("ignores unknown route preload requests", () => {
    expect(() => preloadRoute("/unknown-route")).not.toThrow();
  });
});
