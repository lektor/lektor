import React, { ChangeEvent, KeyboardEvent } from "react";

import RecordComponent, { RecordProps } from "../components/RecordComponent";
import SlideDialog from "../components/SlideDialog";
import { loadData } from "../fetch";
import { getCurrentLanguge, trans } from "../i18n";
import dialogSystem from "../dialogSystem";
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

class FindFiles extends RecordComponent<unknown, State> {
  constructor(props: RecordProps) {
    super(props);
    this.state = {
      query: "",
      currentSelection: -1,
      results: [],
    };
  }

  onInputChange(e: ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;

    if (q === "") {
      this.setState({
        query: "",
        results: [],
        currentSelection: -1,
      });
    } else {
      this.setState({
        query: q,
      });

      loadData(
        "/find",
        { q: q, alt: this.getRecordAlt(), lang: getCurrentLanguge() },
        { method: "POST" }
      ).then((resp) => {
        this.setState((state) => ({
          results: resp.results,
          currentSelection: Math.min(
            state.currentSelection,
            resp.results.length - 1
          ),
        }));
      }, bringUpDialog);
    }
  }

  onInputKey(e: KeyboardEvent) {
    let sel = this.state.currentSelection;
    const max = this.state.results.length;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      sel = (sel + 1) % max;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      sel = (sel - 1 + max) % max;
    } else if (e.key === "Enter") {
      this.onActiveItem(this.state.currentSelection);
    }
    this.setState({
      currentSelection: sel,
    });
  }

  onActiveItem(index: number) {
    const item = this.state.results[index];
    if (item !== undefined) {
      const target =
        this.props.match.params.page === "preview" ? "preview" : "edit";
      const urlPath = this.getUrlRecordPathWithAlt(item.path);
      dialogSystem.dismissDialog();
      this.transitionToAdminPage(target, urlPath);
    }
  }

  selectItem(index: number) {
    this.setState((state) => ({
      currentSelection: Math.min(index, state.results.length - 1),
    }));
  }

  renderResults() {
    const rv = this.state.results.map((result, idx) => {
      const parents = result.parents.map((item, idx) => (
        <span className="parent" key={idx}>
          {item.title}
        </span>
      ));

      return (
        <li
          key={idx}
          className={idx === this.state.currentSelection ? "active" : ""}
          onClick={this.onActiveItem.bind(this, idx)}
          onMouseEnter={this.selectItem.bind(this, idx)}
        >
          {parents}
          <strong>{result.title}</strong>
        </li>
      );
    });

    return <ul className="search-results">{rv}</ul>;
  }

  render() {
    return (
      <SlideDialog hasCloseButton closeOnEscape title={trans("FIND_FILES")}>
        <div className="form-group">
          <input
            type="text"
            autoFocus
            className="form-control"
            value={this.state.query}
            onChange={this.onInputChange.bind(this)}
            onKeyDown={this.onInputKey.bind(this)}
            placeholder={trans("FIND_FILES_PLACEHOLDER")}
          />
        </div>
        {this.renderResults()}
      </SlideDialog>
    );
  }
}

export default FindFiles;
