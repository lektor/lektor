import { it } from "node:test";
import { deepStrictEqual, ok } from "node:assert";
import { lineIsDashes, processBuf, serialize, tokenize } from "./metaformat";

it("metaformat: check whether line just contains of dashes", () => {
  ok(lineIsDashes("----------------"));
  ok(lineIsDashes("      ----------------"));
  ok(lineIsDashes("      ----------------       "));
  ok(!lineIsDashes("----------- -----"));
  ok(!lineIsDashes("----------- -----"));
  ok(!lineIsDashes("-----asdf----"));
  ok(!lineIsDashes("     -----asdf---- "));
});

it("metaformat: process buf", () => {
  deepStrictEqual(processBuf([]), []);
  deepStrictEqual(processBuf([""]), [""]);
  deepStrictEqual(processBuf(["--"]), ["--"]);
  deepStrictEqual(processBuf(["---"]), ["--"]);
  deepStrictEqual(processBuf(["-----"]), ["----"]);
  deepStrictEqual(processBuf(["-----\n"]), ["----"]);
  deepStrictEqual(processBuf(["asdf\n"]), ["asdf"]);
  deepStrictEqual(processBuf(["asdf", "asdf\n"]), ["asdf", "asdf"]);
  deepStrictEqual(processBuf(["a", "----", "asdf\n"]), ["a", "---", "asdf"]);
});

it("metaformat: serialize simple string values", () => {
  deepStrictEqual(serialize([]), []);
  deepStrictEqual(serialize([["test", "test"]]), ["test: test\n"]);
  deepStrictEqual(serialize([["test", "test:test"]]), ["test: test:test\n"]);
  deepStrictEqual(
    serialize([
      ["test", "test"],
      ["test", "test"],
    ]),
    ["test: test\n", "---\n", "test: test\n"],
  );
});

it("metaformat: serialize string values containing newlines or dashes", () => {
  deepStrictEqual(serialize([["test", "tes\nt"]]), [
    "test:\n",
    "\n",
    "tes\n",
    "t\n",
  ]);
  // trailing newline is stripped.
  deepStrictEqual(serialize([["test", "tes\nt\n"]]), [
    "test:\n",
    "\n",
    "tes\n",
    "t\n",
  ]);
  deepStrictEqual(serialize([["test", "tes\n---\nt"]]), [
    "test:\n",
    "\n",
    "tes\n",
    "----\n",
    "t\n",
  ]);
});

it("metaformat: tokenize simple string values", () => {
  deepStrictEqual(tokenize([]), []);
  deepStrictEqual(tokenize([""]), []);
  deepStrictEqual(tokenize(["test: test\n"]), [["test", ["test"]]]);
  deepStrictEqual(tokenize(["test: test\r\n"]), [["test", ["test"]]]);
  deepStrictEqual(tokenize(["test: test:test\n"]), [["test", ["test:test"]]]);
});

it("metaformat: tokenize string values containing newlines or dashes", () => {
  deepStrictEqual(tokenize(["test:\n", "tes\n", "t"]), [
    ["test", ["tes\n", "t"]],
  ]);
  deepStrictEqual(
    tokenize(["---\n", "test:\n", "\n", "tes\n", "----\n", "t\n"]),
    [["test", ["tes\n", "---\n", "t"]]],
  );
  deepStrictEqual(
    tokenize(["---\n \n", "test:\n", "\n", "tes\n", "----\n", "t\n"]),
    [["test", ["tes\n", "---\n", "t"]]],
  );
  deepStrictEqual(tokenize(["test:\n", "\n", "tes\n", "----\n", "t\n"]), [
    ["test", ["tes\n", "---\n", "t"]],
  ]);
});
