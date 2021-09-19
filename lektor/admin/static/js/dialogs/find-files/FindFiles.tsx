import React, { KeyboardEvent, useCallback, useEffect, useState } from "react";

import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import SlideDialog from "../../components/SlideDialog";
import { loadData } from "../../fetch";
import { getCurrentLanguge, trans } from "../../i18n";
import { showErrorDialog } from "../../error-dialog";
import ResultRow from "./ResultRow";
import { useHistory } from "react-router";

export type Result = {
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
  const [results, setResults] = useState<Result[]>([]);
  const [selected, setSelected] = useState(-1);

  const history = useHistory();

  const { alt } = record;

  useEffect(() => {
    if (!query) {
      setResults([]);
      setSelected(-1);
      return;
    }
    let ignore = false;

    loadData(
      "/find",
      { q: query, alt, lang: getCurrentLanguge() },
      { method: "POST" }
    ).then(({ results }) => {
      if (!ignore) {
        setResults(results);
        setSelected((selected) => Math.min(selected, results.length - 1));
      }
    }, showErrorDialog);
    return () => {
      ignore = true;
    };
  }, [alt, query]);

  const goto = useCallback(
    (item: Result) => {
      const target = page === "preview" ? "preview" : "edit";
      const urlPath = getUrlRecordPath(item.path, alt);
      dismiss();
      history.push(pathToAdminPage(target, urlPath));
    },
    [alt, dismiss, history, page]
  );

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
          goto(item);
        }
      }
    },
    [goto, results, selected]
  );

  return (
    <SlideDialog dismiss={dismiss} hasCloseButton title={trans("FIND_FILES")}>
      <div className="form-group">
        <input
          type="text"
          autoFocus
          className="form-control"
          value={query}
          onChange={(ev) => setQuery(ev.target.value)}
          onKeyDown={onInputKey}
          placeholder={trans("FIND_FILES_PLACEHOLDER")}
        />
      </div>
      <ul className="search-results">
        {results.map((result, idx) => (
          <ResultRow
            key={result.path}
            result={result}
            isActive={idx === selected}
            onClick={() => goto(result)}
            onMouseEnter={() => setSelected(idx)}
          />
        ))}
      </ul>
    </SlideDialog>
  );
}

export default FindFiles;
