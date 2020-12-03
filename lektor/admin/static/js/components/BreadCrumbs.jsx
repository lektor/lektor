import React from "react";
import RecordComponent from "./RecordComponent";
import Link from "./Link";
import { loadData } from "../utils";
import i18n from "../i18n";
import makeRichPromise from "../richPromise";
import GlobalActions from "./GlobalActions";

class BreadCrumbs extends RecordComponent {
  constructor(props) {
    super(props);
    this.state = {
      recordPathInfo: null,
    };
  }

  componentDidMount() {
    super.componentDidMount();
    this.updateCrumbs();
  }

  componentDidUpdate(prevProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.updateCrumbs();
    }
  }

  updateCrumbs() {
    const path = this.getRecordPath();
    if (path === null) {
      this.setState({
        recordPathInfo: null,
      });
      return;
    }

    loadData("/pathinfo", { path: path }, makeRichPromise).then((resp) => {
      this.setState({
        recordPathInfo: {
          path: path,
          segments: resp.segments,
        },
      });
    });
  }

  render() {
    let crumbs = [];
    const target =
      this.props.match.params.page === "preview" ? ".preview" : ".edit";
    let lastItem = null;

    if (this.state.recordPathInfo != null) {
      crumbs = this.state.recordPathInfo.segments.map((item) => {
        const urlPath = this.getUrlRecordPathWithAlt(item.path);
        let label = item.label_i18n ? i18n.trans(item.label_i18n) : item.label;
        let className = "record-crumb";

        if (!item.exists) {
          label = item.id;
          className += " missing-record-crumb";
        }
        lastItem = item;

        const adminPath = this.getPathToAdminPage(target, { path: urlPath });

        return (
          <li key={item.path} className={className}>
            <Link to={adminPath}>{label}</Link>
          </li>
        );
      });
    } else {
      crumbs = (
        <li>
          <Link to={this.getPathToAdminPage(".edit", { path: "root" })}>
            {i18n.trans("BACK_TO_OVERVIEW")}
          </Link>
        </li>
      );
    }

    return (
      <div className="breadcrumbs">
        <ul className="breadcrumb container">
          {this.props.children}
          {crumbs}
          {lastItem && lastItem.can_have_children ? (
            <li className="new-record-crumb">
              <Link
                to={this.getPathToAdminPage(".add-child", {
                  path: this.getUrlRecordPathWithAlt(lastItem.path),
                })}
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
