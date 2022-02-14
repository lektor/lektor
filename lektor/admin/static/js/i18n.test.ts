import { promises } from "fs";
import { strictEqual } from "assert";
import { translations } from "./i18n";
import { join } from "path";

const { readdir } = promises;

it("i18n: imports translations for all languages", () => {
  return readdir(join(__dirname, "../../../translations")).then(
    (allTranslations) =>
      strictEqual(
        allTranslations.filter((s) => s.endsWith(".json")).length,
        Object.keys(translations).length
      )
  );
});
