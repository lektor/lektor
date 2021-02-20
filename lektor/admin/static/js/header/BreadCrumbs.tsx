import React, { Component } from "react";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { bringUpDialog } from "../richPromise";

interface RecordPathInfoSegment {
  id: string;
  path: string;
  label: string;
  label_i18n?: Record<string, string>;
  exists: boolean;
  can_have_children: boolean;
}

type State = {
  recordPathInfo: {
    path: string;
    segments: RecordPathInfoSegment[];
  } | null;
};

type Props = RecordProps;

class BreadCrumbs extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { recordPathInfo: null };
  }

  componentDidMount() {
    this.updateCrumbs();
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.updateCrumbs();
    }
  }

  updateCrumbs() {
    const path = this.props.record.path;
    if (path === null) {
      this.setState({ recordPathInfo: null });
    } else {
      loadData("/pathinfo", { path }).then((resp) => {
        this.setState({
          recordPathInfo: { path, segments: resp.segments },
        });
      }, bringUpDialog);
    }
  }

  render() {
    const target =
      this.props.match.params.page === "preview" ? "preview" : "edit";
    const recordPathInfo = this.state.recordPathInfo;
    const lastItem = recordPathInfo
      ? recordPathInfo.segments[recordPathInfo.segments.length - 1]
      : null;

    const crumbs =
      recordPathInfo !== null ? (
        recordPathInfo.segments.map((item) => {
          const urlPath = getUrlRecordPathWithAlt(
            item.path,
            this.props.record.alt
          );
          let label = trans_fallback(item.label_i18n, item.label);
          let className = "breadcrumb-item record-crumb";

          if (!item.exists) {
            label = item.id;
            className += " missing-record-crumb";
          }
          return (
            <li key={item.path} className={className}>
              <Link to={pathToAdminPage(target, urlPath)}>{label}</Link>
            </li>
          );
        })
      ) : (
        <li>
          <Link to={pathToAdminPage("edit", "root")}>
            {trans("BACK_TO_OVERVIEW")}
          </Link>
        </li>
      );

    return (
      <ul className="breadcrumb">
        {crumbs}
        {lastItem && lastItem.can_have_children ? (
          <li className="new-record-crumb">
            <Link
              to={pathToAdminPage(
                "add-child",
                getUrlRecordPathWithAlt(lastItem.path, this.props.record.alt)
              )}
            >
              +
            </Link>
          </li>
        ) : null}
      </ul>
    );
  }
}

export default BreadCrumbs;
