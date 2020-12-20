import { ok, strictEqual } from "assert";
import {
  isValidUrl,
  stripLeadingSlashes,
  stripTrailingSlashes,
  urlPathsConsideredEqual,
  trimSlashes,
  trimColons,
} from "./utils";

describe("Utils", () => {
  it("check URL validity", () => {
    ok(isValidUrl("http://example.com"));
    ok(isValidUrl("https://example.com"));
    ok(!isValidUrl("https:file"));
    ok(!isValidUrl("https:/example.com"));
    ok(isValidUrl("ftp://example.com"));
    ok(isValidUrl("ftps://example.com"));
    ok(!isValidUrl("ftps:/example.com"));
    ok(isValidUrl("mailto:user@example.com"));
    ok(isValidUrl("mailto:anythingreally"));
    ok(!isValidUrl("mailto:with spaces"));
  });

  it("trim strings of slashes and colons", () => {
    strictEqual(stripLeadingSlashes("///asdf"), "asdf");
    strictEqual(stripLeadingSlashes("asdf///"), "asdf///");
    strictEqual(stripLeadingSlashes(""), "");
    strictEqual(stripTrailingSlashes("///asdf"), "///asdf");
    strictEqual(stripTrailingSlashes("asdf///"), "asdf");
    strictEqual(stripTrailingSlashes(""), "");
    strictEqual(trimSlashes("///asdf///"), "asdf");
    strictEqual(trimSlashes("asdf///"), "asdf");
    strictEqual(trimSlashes("///asdf"), "asdf");
    strictEqual(trimSlashes(""), "");
    strictEqual(trimColons(":asdf:"), "asdf");
    strictEqual(trimColons(":asdf:asdf:"), "asdf:asdf");
  });

  it("urlPathsConsideredEqual", () => {
    strictEqual(urlPathsConsideredEqual(null, null), false);
    strictEqual(urlPathsConsideredEqual("asdfs/", null), false);
    strictEqual(urlPathsConsideredEqual("asdfs/", "asdf"), false);
    strictEqual(urlPathsConsideredEqual("asdf/", "asdf"), true);
  });
});
