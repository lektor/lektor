import React, { ChangeEvent, Component, KeyboardEvent } from "react";

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

export type Result = {
  parents: { title: string }[];
  path: string;
  title: string;
};

type State = {
  query: string;
  selected: number;
  results: Result[];
};

type Props = RecordProps & { dismiss: () => void };

class FindFiles extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { query: "", results: [], selected: -1 };

    this.onInputChange = this.onInputChange.bind(this);
    this.onInputKey = this.onInputKey.bind(this);
  }

  onInputChange(event: ChangeEvent<HTMLInputElement>) {
    const query = event.target.value;

    if (query === "") {
      this.setState({ query, results: [], selected: -1 });
    } else {
      this.setState({ query });

      loadData(
        "/find",
        { q: query, alt: this.props.record.alt, lang: getCurrentLanguge() },
        { method: "POST" }
      ).then(({ results }) => {
        this.setState(({ selected }) => ({
          results,
          selected: Math.min(selected, results.length - 1),
        }));
      }, showErrorDialog);
    }
  }

  onInputKey(event: KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      this.setState(({ selected, results }) => ({
        selected: (selected + 1) % results.length,
      }));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      this.setState(({ selected, results }) => ({
        selected: (selected - 1 + results.length) % results.length,
      }));
    } else if (event.key === "Enter") {
      const item = this.state.results[this.state.selected];
      if (item) {
        this.goto(item);
      }
    }
  }

  goto(item: Result) {
    const target = this.props.page === "preview" ? "preview" : "edit";
    const urlPath = getUrlRecordPath(item.path, this.props.record.alt);
    this.props.dismiss();
    this.props.history.push(pathToAdminPage(target, urlPath));
  }

  select(index: number) {
    this.setState((state) => ({
      selected: Math.min(index, state.results.length - 1),
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
              isActive={idx === this.state.selected}
              onClick={this.goto.bind(this, result)}
              onMouseEnter={this.select.bind(this, idx)}
            />
          ))}
        </ul>
      </SlideDialog>
    );
  }
}

export default FindFiles;
