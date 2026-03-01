import { it } from "node:test";
import { strictEqual } from "node:assert";
import { getFieldColumns } from "./widgets";

it("widgets: getFieldColumns", () => {
  strictEqual(getFieldColumns({ type: { width: "1/1" } }), 12);
  strictEqual(getFieldColumns({ type: { width: "1/3" } }), 4);
  strictEqual(getFieldColumns({ type: { width: "2/4" } }), 6);
  strictEqual(getFieldColumns({ type: { width: "3/7" } }), 5);
  strictEqual(getFieldColumns({ type: { width: "1/100" } }), 2);
  // rounded down
  strictEqual(getFieldColumns({ type: { width: "49/100" } }), 5);
  strictEqual(getFieldColumns({ type: { width: "50/100" } }), 6);
  strictEqual(getFieldColumns({ type: { width: "asdf" } }), 12);
  strictEqual(getFieldColumns({ type: { width: "as/df" } }), 12);
});
