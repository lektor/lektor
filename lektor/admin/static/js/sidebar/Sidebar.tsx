import React, { Component } from "react";
import { loadData } from "../fetch";
import { trans_obj } from "../i18n";
import { RecordProps } from "../components/RecordComponent";
import { showErrorDialog } from "../error-dialog";
import { Alternative, RecordInfo } from "../components/types";
import PageActions from "./PageActions";
import Alternatives from "./Alternatives";
import AttachmentActions from "./AttachmentActions";
import { CHILDREN_PER_PAGE } from "./constants";
import ChildActions from "./ChildActions";
import { subscribe, unsubscribe } from "../events";

/**
 * Keep a cache of the page number in the list of subpages that we are currently
 * on. Only keeps this page number in memory for the last five records.
 */
export class ChildPosCache {
  private memo: [record: string, page: number][];

  constructor() {
    this.memo = [];
  }

  /** Remember the page for a record. */
  rememberPosition(record: string, page: number): void {
    // remove current value
    this.memo = this.memo.filter(([r]) => r !== record);
    this.memo.unshift([record, page]);
    if (this.memo.length > 5) {
      this.memo.length = 5;
    }
  }

  getPosition(record: string, childCount: number): number {
    const page = this.memo.find(([r]) => r === record)?.[1];
    return page ? Math.min(page, Math.ceil(childCount / CHILDREN_PER_PAGE)) : 1;
  }
}

type State = {
  recordInfo: RecordInfo | null;
  recordAlts: Alternative[];
  lastRecordRequest: string | null;
  childrenPage: number;
};

const initialState: State = {
  recordInfo: null,
  recordAlts: [],
  lastRecordRequest: null,
  childrenPage: 1,
};

type Props = Pick<RecordProps, "record" | "page">;

class Sidebar extends Component<Props, State> {
  childPosCache: ChildPosCache;

  constructor(props: Props) {
    super(props);

    this.state = initialState;
    this.childPosCache = new ChildPosCache();

    this.onAttachmentsChanged = this.onAttachmentsChanged.bind(this);
  }

  componentDidMount() {
    this._updateRecordInfo();
    subscribe("lektor-attachments-changed", this.onAttachmentsChanged);
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.record.path !== this.props.record.path) {
      this._updateRecordInfo();
    }
  }

  componentWillUnmount() {
    unsubscribe("lektor-attachments-changed", this.onAttachmentsChanged);
  }

  onAttachmentsChanged(event: CustomEvent<string>) {
    if (event.detail === this.props.record.path) {
      this._updateRecordInfo();
    }
  }

  _updateRecordInfo() {
    const path = this.props.record.path;
    if (path === null) {
      this.setState(initialState);
      return;
    }

    this.setState({ lastRecordRequest: path }, () => {
      loadData("/recordinfo", { path: path }).then((resp: RecordInfo) => {
        // we're already fetching something else.
        if (path !== this.state.lastRecordRequest) {
          return;
        }
        this.setState({
          recordInfo: resp,
          recordAlts: resp.alts.sort((a, b) => {
            const nameA = (a.is_primary ? "A" : "B") + trans_obj(a.name_i18n);
            const nameB = (b.is_primary ? "A" : "B") + trans_obj(b.name_i18n);
            return nameA === nameB ? 0 : nameA < nameB ? -1 : 1;
          }),
          childrenPage: this.childPosCache.getPosition(
            path,
            resp.children.length
          ),
        });
      }, showErrorDialog);
    });
  }

  render() {
    const { record, page } = this.props;
    const { recordInfo } = this.state;
    return (
      <div className="sidebar-wrapper">
        {record.path !== null && recordInfo && (
          <PageActions record={record} recordInfo={recordInfo} />
        )}
        <Alternatives
          record={record}
          page={page}
          recordAlts={this.state.recordAlts}
        />
        {recordInfo?.can_have_children && (
          <ChildActions
            target={page === "preview" ? "preview" : "edit"}
            allChildren={recordInfo.children}
            record={record}
            page={this.state.childrenPage}
            setPage={(page) => {
              this.childPosCache.rememberPosition(record.path, page);
              this.setState({ childrenPage: page });
            }}
          />
        )}
        {recordInfo?.can_have_attachments && (
          <AttachmentActions record={record} recordInfo={recordInfo} />
        )}
      </div>
    );
  }
}

export default Sidebar;
