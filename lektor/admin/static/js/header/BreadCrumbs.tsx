import React, { ReactNode } from "react";
import RecordComponent, {
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import { bringUpDialog } from "../richPromise";
import GlobalActions from "./GlobalActions";

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

type Props = { children: ReactNode } & RecordProps;

class BreadCrumbs extends RecordComponent<Props, State> {
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
    const path = this.getRecordPath();
    if (path === null) {
      this.setState({ recordPathInfo: null });
    } else {
      loadData("/pathinfo", { path: path }).then((resp) => {
        this.setState({
          recordPathInfo: { path: path, segments: resp.segments },
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
      recordPathInfo != null ? (
        recordPathInfo.segments.map((item) => {
          const urlPath = this.getUrlRecordPathWithAlt(item.path);
          let label = item.label_i18n ? trans(item.label_i18n) : item.label;
          let className = "record-crumb";

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
      <div className="breadcrumbs">
        <ul className="breadcrumb container">
          {this.props.children}
          {crumbs}
          {lastItem && lastItem.can_have_children ? (
            <li className="new-record-crumb">
              <Link
                to={pathToAdminPage(
                  "add-child",
                  this.getUrlRecordPathWithAlt(lastItem.path)
                )}
              >
                +
              </Link>
            </li>
          ) : null}
          {" " /* this space is needed for chrome ... */}
          <li className="meta">
            <GlobalActions {...this.props} />
          </li>
        </ul>
      </div>
    );
  }
}

export default BreadCrumbs;
