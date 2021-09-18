import React, { Component } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";

interface RecordPathInfoSegment {
  id: string;
  path: string;
  label: string;
  label_i18n?: Record<string, string>;
  exists: boolean;
  can_have_children: boolean;
}

function Crumbs({
  alt,
  segments,
  target,
}: {
  alt: string;
  segments: RecordPathInfoSegment[];
  target: "preview" | "edit";
}) {
  return (
    <>
      {segments.map((item) => {
        const { path, exists } = item;
        const urlPath = getUrlRecordPath(path, alt);
        const label = exists
          ? trans_fallback(item.label_i18n, item.label)
          : item.id;
        const className = exists
          ? "breadcrumb-item record-crumb"
          : "breadcrumb-item record-crumb missing-record-crumb";
        return (
          <li key={path} className={className}>
            <Link to={pathToAdminPage(target, urlPath)}>{label}</Link>
          </li>
        );
      })}
    </>
  );
}

function AddNewPage({
  alt,
  lastItem,
}: {
  alt: string;
  lastItem: RecordPathInfoSegment;
}) {
  return lastItem?.can_have_children ? (
    <li className="new-record-crumb">
      <Link
        to={pathToAdminPage("add-child", getUrlRecordPath(lastItem.path, alt))}
      >
        +
      </Link>
    </li>
  ) : null;
}

type State = {
  segments: RecordPathInfoSegment[] | null;
};

type Props = Pick<RecordProps, "record" | "page">;

class BreadCrumbs extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { segments: null };
  }

  componentDidMount() {
    this.updateCrumbs();
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.record.path !== this.props.record.path) {
      this.updateCrumbs();
    }
  }

  updateCrumbs() {
    const path = this.props.record.path;
    if (path === null) {
      this.setState({ segments: null });
    } else {
      loadData("/pathinfo", { path }).then((resp) => {
        this.setState({ segments: resp.segments });
      }, showErrorDialog);
    }
  }

  render() {
    const { segments } = this.state;
    if (!segments) {
      return (
        <ul className="breadcrumb">
          <li>
            <Link to={pathToAdminPage("edit", "root")}>
              {trans("BACK_TO_OVERVIEW")}
            </Link>
          </li>
        </ul>
      );
    }

    const { alt } = this.props.record;
    const target = this.props.page === "preview" ? "preview" : "edit";
    const lastItem = segments[segments.length - 1];

    return (
      <ul className="breadcrumb">
        <Crumbs segments={segments} alt={alt} target={target} />
        <AddNewPage lastItem={lastItem} alt={alt} />
      </ul>
    );
  }
}

export default BreadCrumbs;
