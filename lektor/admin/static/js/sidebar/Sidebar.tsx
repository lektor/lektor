import React, { Component, MouseEvent } from "react";
import { loadData } from "../fetch";
import { trans, trans_obj } from "../i18n";
import hub from "../hub";
import { AttachmentsChangedEvent } from "../events";
import {
  getUrlRecordPathWithAlt,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { bringUpDialog } from "../richPromise";
import { Alternative, RecordInfo } from "../components/types";
import PageActions from "./PageActions";
import Alternatives from "./Alternatives";
import AttachmentActions from "./AttachmentActions";

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
            const nameA = (a.is_primary ? "A" : "B") + trans_obj(a.name_i18n);
            const nameB = (b.is_primary ? "A" : "B") + trans_obj(b.name_i18n);
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
                    {trans_obj(child.label_i18n)}
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

  render() {
    return (
      <div className="sidebar-wrapper">
        {this.props.record.path !== null && this.state.recordInfo && (
          <PageActions
            {...this.props}
            recordInfo={this.state.recordInfo}
          ></PageActions>
        )}
        <Alternatives
          {...this.props}
          recordAlts={this.state.recordAlts}
        ></Alternatives>
        {this.state.recordInfo?.can_have_children && this.renderChildActions()}
        {this.state.recordInfo?.can_have_attachments && (
          <AttachmentActions
            {...this.props}
            recordInfo={this.state.recordInfo}
          ></AttachmentActions>
        )}
      </div>
    );
  }
}

export default Sidebar;
