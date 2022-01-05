/* eslint-env mocha */
import { deepStrictEqual } from "assert";
import { getRecordDetails } from "./RecordComponent";

it("Get Record path and alt", () => {
  deepStrictEqual(getRecordDetails(""), null);
  deepStrictEqual(getRecordDetails("root:about"), {
    path: "/about",
    alt: "_primary",
  });
  deepStrictEqual(getRecordDetails("root+fr"), {
    path: "",
    alt: "fr",
  });
  deepStrictEqual(getRecordDetails("testroot"), null);
  deepStrictEqual(getRecordDetails("testroot+fr"), null);
  deepStrictEqual(getRecordDetails("root:blog+fr"), {
    path: "/blog",
    alt: "fr",
  });
});
