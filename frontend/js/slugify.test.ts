import { describe, it } from "node:test";
import { strictEqual } from "node:assert";
import { slugify } from "./slugify";

describe("slugs", () => {
  it("slugify strings", () => {
    strictEqual(slugify("asdf asdf"), "asdf-asdf");
    strictEqual(slugify("äasdf asdf"), "aeasdf-asdf");
    strictEqual(slugify("<3"), "love");
    strictEqual(slugify("€"), "euro");
    strictEqual(slugify("&"), "and");
    strictEqual(slugify("..€.."), "euro");
  });
});
