import { it } from "node:test";
import { readdir } from "node:fs/promises";
import { strictEqual } from "node:assert";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { translations } from "./i18n";

const filename = fileURLToPath(import.meta.url);
const __dirname = dirname(filename);

it("i18n: imports translations for all languages", () => {
  return readdir(join(__dirname, "..", "..", "lektor", "translations")).then(
    (allTranslations) => {
      strictEqual(
        allTranslations.filter((s) => s.endsWith(".json")).length,
        Object.keys(translations).length,
      );
    },
  );
});
