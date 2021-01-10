import { deepStrictEqual, strictEqual } from "assert";
import { parseFlowFormat } from "./FlowWidget";

const rawFlowBlock = `#### text ####
text: Text from text only flow block.
#### text_and_html ####
text: Text from text_and_html flow block.`;

describe("FlowWidget", () => {
  it("Parses flow format", () => {
    deepStrictEqual(parseFlowFormat(rawFlowBlock), [
      ["text", ["text: Text from text only flow block."]],
      ["text_and_html", ["text: Text from text_and_html flow block."]],
    ]);
    strictEqual(parseFlowFormat("# BADFORMA#"), null);
  });
});
