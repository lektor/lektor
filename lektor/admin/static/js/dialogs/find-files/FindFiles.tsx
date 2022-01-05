import React, { KeyboardEvent, useCallback, useEffect, useState } from "react";

import { RecordProps } from "../../components/RecordComponent";
import SlideDialog from "../../components/SlideDialog";
import { post } from "../../fetch";
import { getCurrentLanguge, trans } from "../../i18n";
import { showErrorDialog } from "../../error-dialog";
import ResultRow from "./ResultRow";
import { useGoToAdminPage } from "../../components/use-go-to-admin-page";

export type SearchResult = {
  parents: { title: string }[];
  path: string;
  title: string;
};

function FindFiles({
  page,
  record,
  dismiss,
}: RecordProps & { dismiss: () => void }): JSX.Element {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState(-1);

  const goToAdminPage = useGoToAdminPage();

  const { alt } = record;
  const target = page === "preview" ? "preview" : "edit";

  useEffect(() => {
    if (!query) {
      setResults([]);
      setSelected(-1);
      return;
    }
    let ignore = false;

    post("/find", { q: query, alt, lang: getCurrentLanguge() }).then(
      ({ results }) => {
        if (!ignore) {
          setResults(results);
          setSelected((selected) => Math.min(selected, results.length - 1));
        }
      },
      showErrorDialog
    );
    return () => {
      ignore = true;
    };
  }, [alt, query]);

  const onInputKey = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelected((selected) => (selected + 1) % results.length);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelected(
          (selected) => (selected - 1 + results.length) % results.length
        );
      } else if (event.key === "Enter") {
        const item = results[selected];
        if (item) {
          dismiss();
          goToAdminPage(target, item.path, alt);
        }
      }
    },
    [alt, dismiss, goToAdminPage, results, selected, target]
  );

  return (
    <SlideDialog dismiss={dismiss} hasCloseButton title={trans("FIND_FILES")}>
      <input
        type="text"
        autoFocus
        className="form-control"
        value={query}
        onChange={(ev) => setQuery(ev.target.value)}
        onKeyDown={onInputKey}
        placeholder={trans("FIND_FILES_PLACEHOLDER")}
      />
      <ul className="search-results">
        {results.map((result, idx) => (
          <ResultRow
            key={result.path}
            result={result}
            isActive={idx === selected}
            dismiss={dismiss}
            alt={record.alt}
            target={target}
          />
        ))}
      </ul>
    </SlideDialog>
  );
}

export default FindFiles;
