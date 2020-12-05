/* eslint-env mocha */
import { ok } from "assert";
import { isValidUrl } from "./utils";

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
});
