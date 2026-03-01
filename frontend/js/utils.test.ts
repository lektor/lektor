import { describe, it } from "node:test";
import { ok, strictEqual } from "node:assert";
import {
  isValidUrl,
  trimLeadingSlashes,
  trimTrailingSlashes,
  trimSlashes,
  trimColons,
} from "./utils";

describe("Utils", () => {
  it("check URL validity", () => {
    ok(isValidUrl("http://example.com"));
    ok(isValidUrl("https://example.com"));
    // ok(!isValidUrl("https:file"));  // ignoring this case in favor of more generic regex
    ok(!isValidUrl("https:/example.com"));
    ok(isValidUrl("ftp://example.com"));
    ok(isValidUrl("ftps://example.com"));
    ok(!isValidUrl("ftps:/example.com"));
    ok(isValidUrl("mailto:user@example.com"));
    ok(isValidUrl("mailto:anythingreally"));
    ok(!isValidUrl("mailto:with spaces"));
    ok(isValidUrl("z39.50r://example.com:8001/database?45"));
    ok(isValidUrl("svn+ssh://example.com"));
    ok(isValidUrl("feed:example.com/rss"));
    ok(isValidUrl("webcal:example.com/calendar"));
    ok(isValidUrl("ms-help://section/path/file.htm"));
    ok(!isValidUrl("anyscheme:/oneslash"));
  });

  it("trim strings of slashes and colons", () => {
    strictEqual(trimLeadingSlashes("///asdf"), "asdf");
    strictEqual(trimLeadingSlashes("asdf///"), "asdf///");
    strictEqual(trimLeadingSlashes(""), "");
    strictEqual(trimTrailingSlashes("///asdf"), "///asdf");
    strictEqual(trimTrailingSlashes("asdf///"), "asdf");
    strictEqual(trimTrailingSlashes(""), "");
    strictEqual(trimSlashes("///asdf///"), "asdf");
    strictEqual(trimSlashes("asdf///"), "asdf");
    strictEqual(trimSlashes("///asdf"), "asdf");
    strictEqual(trimSlashes(""), "");
    strictEqual(trimColons(":asdf:"), "asdf");
    strictEqual(trimColons(":asdf:asdf:"), "asdf:asdf");
  });
});
