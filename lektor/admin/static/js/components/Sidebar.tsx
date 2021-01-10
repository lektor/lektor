import React, { Component, MouseEvent } from "react";
import { getPlatform } from "../utils";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import hub from "../hub";
import { AttachmentsChangedEvent } from "../events";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "./RecordComponent";
import Link from "./Link";
import { bringUpDialog } from "../richPromise";
import { Alternative, RecordInfo } from "./types";

const getBrowseButtonTitle = () => {
  const platform = getPlatform();
  if (platform === "mac") {
    return trans("BROWSE_FS_MAC");
  } else if (platform === "windows") {
    return trans("BROWSE_FS_WINDOWS");
  } else {
    return trans("BROWSE_FS");
  }
};

const CHILDREN_PER_PAGE = 15;

class ChildPosCache {
  memo: [record: string, page: number][];

  constructor() {
    this.memo = [];
  }

  rememberPosition(record: string, page: number): void {
    for (let i = 0; i < this.memo.length; i++) {
      if (this.memo[i][0] === record) {
        this.memo[i][1] = page;
        return;
      }
    }
    this.memo.unshift([record, page]);
    if (this.memo.length > 5) {
      this.memo.length = 5;
    }
  }

  getPosition(record: string, childCount: number): number {
    for (let i = 0; i < this.memo.length; i++) {
      if (this.memo[i][0] === record) {
        let rv = this.memo[i][1];
        if (childCount !== undefined) {
          rv = Math.min(rv, Math.ceil(childCount / CHILDREN_PER_PAGE));
        }
        return rv;
      }
    }
    return 1;
  }
}

type State = {
  recordInfo: RecordInfo | null;
  recordAlts: Alternative[];
  lastRecordRequest: string | null;
  childrenPage: number;
};

class Sidebar extends Component<RecordProps, State> {
  childPosCache: ChildPosCache;

  constructor(props: RecordProps) {
    super(props);

    this.state = this._getInitialState();
    this.childPosCache = new ChildPosCache();

    this.onAttachmentsChanged = this.onAttachmentsChanged.bind(this);
    this.fsOpen = this.fsOpen.bind(this);
  }

  _getInitialState() {
    return {
      recordInfo: null,
      recordAlts: [],
      lastRecordRequest: null,
      childrenPage: 1,
    };
  }

  componentDidMount() {
    this._updateRecordInfo();

    hub.subscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
  }

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this._updateRecordInfo();
    }
  }

  componentWillUnmount() {
    hub.unsubscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
  }

  onAttachmentsChanged(event: AttachmentsChangedEvent) {
    if (event.recordPath === this.props.record.path) {
      this._updateRecordInfo();
    }
  }

  _updateRecordInfo() {
    const path = this.props.record.path;
    if (path === null) {
      this.setState(this._getInitialState());
      return;
    }

    this.setState(
      {
        lastRecordRequest: path,
      },
      () => {
        loadData("/recordinfo", { path: path }).then((resp: RecordInfo) => {
          // we're already fetching something else.
          if (path !== this.state.lastRecordRequest) {
            return;
          }
          const alts: Alternative[] = resp.alts;
          alts.sort((a, b) => {
            const nameA = (a.is_primary ? "A" : "B") + trans(a.name_i18n);
            const nameB = (b.is_primary ? "A" : "B") + trans(b.name_i18n);
            return nameA === nameB ? 0 : nameA < nameB ? -1 : 1;
          });
          this.setState({
            recordInfo: resp,
            recordAlts: alts,
            childrenPage: this.childPosCache.getPosition(
              path,
              resp.children.length
            ),
          });
        }, bringUpDialog);
      }
    );
  }

  fsOpen(event: MouseEvent) {
    event.preventDefault();
    loadData(
      "/browsefs",
      { path: this.props.record.path, alt: this.props.record.alt },
      { method: "POST" }
    ).then((resp) => {
      if (!resp.okay) {
        alert(trans("ERROR_CANNOT_BROWSE_FS"));
      }
    }, bringUpDialog);
  }

  renderPageActions() {
    const urlPath = getUrlRecordPathWithAlt(
      this.props.record.path,
      this.props.record.alt
    );

    const { recordInfo } = this.state;
    if (!recordInfo) {
      return null;
    }

    const title = recordInfo.is_attachment
      ? trans("ATTACHMENT_ACTIONS")
      : trans("PAGE_ACTIONS");

    return (
      <div key="actions" className="section">
        <h3>{title}</h3>
        <ul className="nav">
          <li key="edit">
            <Link to={`${urlPath}/edit`}>
              {recordInfo.is_attachment
                ? trans("EDIT_METADATA")
                : trans("EDIT")}
            </Link>
          </li>
          {recordInfo.can_be_deleted && (
            <li key="delete">
              <Link to={`${urlPath}/delete`}>{trans("DELETE")}</Link>
            </li>
          )}
          <li key="preview">
            <Link to={`${urlPath}/preview`}>{trans("PREVIEW")}</Link>
          </li>
          {recordInfo.exists && (
            <li key="fs-open">
              <a href="#" onClick={this.fsOpen}>
                {getBrowseButtonTitle()}
              </a>
            </li>
          )}
          {recordInfo.can_have_children && (
            <li key="add-child">
              <Link to={`${urlPath}/add-child`}>{trans("ADD_CHILD_PAGE")}</Link>
            </li>
          )}
          {recordInfo.can_have_attachments && (
            <li key="add-attachment">
              <Link to={`${urlPath}/upload`}>{trans("ADD_ATTACHMENT")}</Link>
            </li>
          )}
        </ul>
      </div>
    );
  }

  renderAlts() {
    if (this.state.recordAlts.length < 2) {
      return null;
    }

    const items = this.state.recordAlts.map((item) => {
      let title = trans(item.name_i18n);
      let className = "alt";
      if (item.is_primary) {
        title += " (" + trans("PRIMARY_ALT") + ")";
      } else if (item.primary_overlay) {
        title += " (" + trans("PRIMARY_OVERLAY") + ")";
      }
      if (!item.exists) {
        className += " alt-missing";
      }

      const path = pathToAdminPage(
        this.props.match.params.page,
        getUrlRecordPathWithAlt(this.props.record.path, item.alt)
      );
      return (
        <li key={item.alt} className={className}>
          <Link to={path}>{title}</Link>
        </li>
      );
    });

    return (
      <div key="alts" className="section">
        <h3>{trans("ALTS")}</h3>
        <ul className="nav">{items}</ul>
      </div>
    );
  }

  renderChildPagination() {
    const children = this.state.recordInfo?.children ?? [];
    const pages = Math.ceil(children.length / CHILDREN_PER_PAGE);
    if (pages <= 1) {
      return null;
    }
    const page = this.state.childrenPage;
    const goToPage = (diff: number, event: MouseEvent) => {
      event.preventDefault();
      const newPage = page + diff;
      const recordPath = this.props.record.path;
      if (recordPath) {
        this.childPosCache.rememberPosition(recordPath, newPage);
      }
      this.setState({ childrenPage: newPage });
    };

    return (
      <li className="pagination">
        {page > 1 ? (
          <a href="#" onClick={goToPage.bind(this, -1)}>
            «
          </a>
        ) : (
          <em>«</em>
        )}
        <span className="page">{page + " / " + pages}</span>
        {page < pages ? (
          <a href="#" onClick={goToPage.bind(this, +1)}>
            »
          </a>
        ) : (
          <em>»</em>
        )}
      </li>
    );
  }

  renderChildActions() {
    const target =
      this.props.match.params.page === "preview" ? "preview" : "edit";

    const allChildren = this.state.recordInfo?.children ?? [];
    const children = allChildren.slice(
      (this.state.childrenPage - 1) * CHILDREN_PER_PAGE,
      this.state.childrenPage * CHILDREN_PER_PAGE
    );

    return (
      <div key="children" className="section">
        <h3>{trans("CHILD_PAGES")}</h3>
        <ul className="nav record-children">
          {this.renderChildPagination()}
          {children.length > 0 ? (
            children.map((child) => {
              const urlPath = getUrlRecordPathWithAlt(
                child.path,
                this.props.record.alt
              );
              return (
                <li key={child.id}>
                  <Link to={`${urlPath}/${target}`}>
                    {trans(child.label_i18n)}
                  </Link>
                </li>
              );
            })
          ) : (
            <li key="_missing">
              <em>{trans("NO_CHILD_PAGES")}</em>
            </li>
          )}
        </ul>
      </div>
    );
  }

  renderAttachmentActions() {
    const attachments = this.state.recordInfo?.attachments ?? [];
    return (
      <div key="attachments" className="section">
        <h3>{trans("ATTACHMENTS")}</h3>
        <ul className="nav record-attachments">
          {attachments.length > 0 ? (
            attachments.map((atch) => {
              const urlPath = getUrlRecordPathWithAlt(
                atch.path,
                this.props.record.alt
              );
              return (
                <li key={atch.id}>
                  <Link to={`${urlPath}/edit`}>
                    {atch.id} ({atch.type})
                  </Link>
                </li>
              );
            })
          ) : (
            <li key="_missing">
              <em>{trans("NO_ATTACHMENTS")}</em>
            </li>
          )}
        </ul>
      </div>
    );
  }

  render() {
    return (
      <div className="sidebar-wrapper">
        {this.props.record.path !== null && this.renderPageActions()}
        {this.renderAlts()}
        {this.state.recordInfo?.can_have_children && this.renderChildActions()}
        {this.state.recordInfo?.can_have_attachments &&
          this.renderAttachmentActions()}
      </div>
    );
  }
}

export default Sidebar;
