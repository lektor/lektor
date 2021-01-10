import React, { ChangeEvent, Component, KeyboardEvent } from "react";

import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import SlideDialog from "../components/SlideDialog";
import { loadData } from "../fetch";
import { getCurrentLanguge, trans } from "../i18n";
import { bringUpDialog } from "../richPromise";

type Result = {
  parents: { title: string }[];
  path: string;
  title: string;
};

type State = {
  query: string;
  currentSelection: number;
  results: Result[];
};

function ResultRow({
  result,
  isActive,
  onClick,
  onMouseEnter,
}: {
  result: Result;
  isActive: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}) {
  return (
    <li
      className={isActive ? "active" : ""}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
    >
      {result.parents.map((item, idx) => (
        <span className="parent" key={idx}>
          {item.title}
        </span>
      ))}
      <strong>{result.title}</strong>
    </li>
  );
}

type Props = RecordProps & { dismiss: () => void };

class FindFiles extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { query: "", results: [], currentSelection: -1 };

    this.onInputChange = this.onInputChange.bind(this);
    this.onInputKey = this.onInputKey.bind(this);
  }

  onInputChange(event: ChangeEvent<HTMLInputElement>) {
    const query = event.target.value;

    if (query === "") {
      this.setState({ query, results: [], currentSelection: -1 });
    } else {
      this.setState({ query });

      loadData(
        "/find",
        { q: query, alt: this.props.record.alt, lang: getCurrentLanguge() },
        { method: "POST" }
      ).then(({ results }) => {
        this.setState(({ currentSelection }) => ({
          results,
          currentSelection: Math.min(currentSelection, results.length - 1),
        }));
      }, bringUpDialog);
    }
  }

  onInputKey(event: KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      this.setState(({ currentSelection, results }) => ({
        currentSelection: (currentSelection + 1) % results.length,
      }));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      this.setState(({ currentSelection, results }) => ({
        currentSelection:
          (currentSelection - 1 + results.length) % results.length,
      }));
    } else if (event.key === "Enter") {
      this.onActiveItem(this.state.currentSelection);
    }
  }

  onActiveItem(index: number) {
    const item = this.state.results[index];
    if (item !== undefined) {
      const target =
        this.props.match.params.page === "preview" ? "preview" : "edit";
      const urlPath = getUrlRecordPathWithAlt(item.path, this.props.record.alt);
      this.props.dismiss();
      this.props.history.push(pathToAdminPage(target, urlPath));
    }
  }

  selectItem(index: number) {
    this.setState((state) => ({
      currentSelection: Math.min(index, state.results.length - 1),
    }));
  }

  render() {
    return (
      <SlideDialog
        dismiss={this.props.dismiss}
        hasCloseButton
        title={trans("FIND_FILES")}
      >
        <div className="form-group">
          <input
            type="text"
            autoFocus
            className="form-control"
            value={this.state.query}
            onChange={this.onInputChange}
            onKeyDown={this.onInputKey}
            placeholder={trans("FIND_FILES_PLACEHOLDER")}
          />
        </div>
        <ul className="search-results">
          {this.state.results.map((result, idx) => (
            <ResultRow
              key={idx}
              result={result}
              isActive={idx === this.state.currentSelection}
              onClick={this.onActiveItem.bind(this, idx)}
              onMouseEnter={this.selectItem.bind(this, idx)}
            />
          ))}
        </ul>
      </SlideDialog>
    );
  }
}

export default FindFiles;
