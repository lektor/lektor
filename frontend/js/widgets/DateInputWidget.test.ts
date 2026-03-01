import { it } from "node:test";
import { strictEqual } from "node:assert";
import { translations } from "../i18n";
import { isValidDate, postprocessDate, validateDate } from "./DateInputWidget";

it("DateInputWidget - date validation", () => {
  strictEqual(isValidDate(2012, 12, 12), true);
  strictEqual(isValidDate(2012, 12, 222), false);
  strictEqual(isValidDate(2012, 322, 12), false);
  strictEqual(isValidDate(3333, 12, 12), true);
});

it("DateInputWidget - string date validation", () => {
  strictEqual(validateDate(""), null);
  strictEqual(validateDate("2012-12-12"), null);
  strictEqual(validateDate("2012-12-1s2"), translations.en.ERROR_INVALID_DATE);
});

it("DateInputWidget - post process date", () => {
  strictEqual(postprocessDate("2012-12-12"), "2012-12-12");
  strictEqual(postprocessDate("2012-12-12  "), "2012-12-12");
  strictEqual(postprocessDate("  2012-12-12  "), "2012-12-12");
  strictEqual(postprocessDate("1.2.2020"), "2020-02-01");
});
