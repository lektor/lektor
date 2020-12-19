import { ok, strictEqual } from "assert";
import {
  isValidUrl,
  stripLeadingSlash,
  stripTrailingSlash,
  urlPathsConsideredEqual,
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

  it("strip slashes", () => {
    strictEqual(stripLeadingSlash("///asdf"), "asdf");
    strictEqual(stripLeadingSlash("asdf///"), "asdf///");
    strictEqual(stripLeadingSlash(""), "");
    strictEqual(stripTrailingSlash("///asdf"), "///asdf");
    strictEqual(stripTrailingSlash("asdf///"), "asdf");
    strictEqual(stripTrailingSlash(""), "");
  });

  it("urlPathsConsideredEqual", () => {
    strictEqual(urlPathsConsideredEqual(null, null), false);
    strictEqual(urlPathsConsideredEqual("asdfs/", null), false);
    strictEqual(urlPathsConsideredEqual("asdfs/", "asdf"), false);
    strictEqual(urlPathsConsideredEqual("asdf/", "asdf"), true);
  });
});
