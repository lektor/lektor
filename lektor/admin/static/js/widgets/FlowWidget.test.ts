import { deepStrictEqual, strictEqual } from "assert";
import { parseFlowFormat, serializeFlowFormat } from "./FlowWidget";

const rawFlowBlock = `#### text ####
text: Text from text only flow block.
#### text_and_html ####
text: Text from text_and_html flow block.`;

it("flow format: parses flow format", () => {
  deepStrictEqual(parseFlowFormat(rawFlowBlock), [
    ["text", ["text: Text from text only flow block."]],
    ["text_and_html", ["text: Text from text_and_html flow block."]],
  ]);
  strictEqual(parseFlowFormat("# BADFORMA#"), null);
});

it("flow format: serialises flow format", () => {
  deepStrictEqual(
    serializeFlowFormat([
      ["text", ["text: Text from text only flow block.\n"]],
      ["text_and_html", ["text: Text from text_and_html flow block.\n"]],
    ]),
    rawFlowBlock
  );
  deepStrictEqual(
    serializeFlowFormat([
      ["text", ["text: Text from text only flow block.\n"]],
      ["text_and_html", ["text: Text from text_and_html flow block."]],
    ]),
    rawFlowBlock
  );
});
