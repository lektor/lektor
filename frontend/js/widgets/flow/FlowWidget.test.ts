import { it } from "node:test";
import { deepStrictEqual } from "node:assert";
import { parseFlowFormat, serializeFlowFormat } from "./FlowWidget";

const rawFlowBlock = `#### text ####
text: Text from text only flow block.
#### text_and_html ####
text: Text from text_and_html flow block.`;

const parsed = [
  ["text", ["text: Text from text only flow block."]],
  ["text_and_html", ["text: Text from text_and_html flow block."]],
];

it("flow format: parses flow format", () => {
  deepStrictEqual(parseFlowFormat(undefined), []);
  deepStrictEqual(parseFlowFormat(`asdfasdf`), []);
  deepStrictEqual(parseFlowFormat(rawFlowBlock), parsed);
  deepStrictEqual(parseFlowFormat("           \n" + rawFlowBlock), parsed);
  deepStrictEqual(parseFlowFormat("# BADFORMA#"), []);
  deepStrictEqual(parseFlowFormat(`#### test ####\n#####test#####`), [
    ["test", ["####test####"]],
  ]);
});

it("flow format: serialises flow format", () => {
  deepStrictEqual(
    serializeFlowFormat([
      ["text", ["text: Text from text only flow block.\n"]],
      ["text_and_html", ["text: Text from text_and_html flow block.\n"]],
    ]),
    rawFlowBlock,
  );
  deepStrictEqual(
    serializeFlowFormat([
      ["text", ["text: Text from text only flow block.\n"]],
      ["text_and_html", ["text: Text from text_and_html flow block."]],
    ]),
    rawFlowBlock,
  );
});
