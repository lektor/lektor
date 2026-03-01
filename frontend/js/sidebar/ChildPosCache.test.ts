import { it } from "node:test";
import { strictEqual } from "node:assert";
import { ChildPosCache } from "./Sidebar";

it("sidebar: child page position cache", () => {
  const cache = new ChildPosCache();
  strictEqual(cache.getPosition("test", 50), 1);
  cache.rememberPosition("test", 4);
  strictEqual(cache.getPosition("test", 50), 4);
  cache.rememberPosition("test", 2);
  strictEqual(cache.getPosition("test", 50), 2);
  cache.rememberPosition("test2", 3);
  strictEqual(cache.getPosition("test", 50), 2);
  strictEqual(cache.getPosition("test2", 50), 3);
});
