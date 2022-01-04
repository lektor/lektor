import React, { useEffect, useReducer, useState } from "react";
import { get } from "../fetch";
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

const compareAlternatives = (a: Alternative, b: Alternative) => {
  const nameA = (a.is_primary ? "A" : "B") + trans_obj(a.name_i18n);
  const nameB = (b.is_primary ? "A" : "B") + trans_obj(b.name_i18n);
  return nameA === nameB ? 0 : nameA < nameB ? -1 : 1;
};

function Sidebar({ record, page }: RecordProps): JSX.Element | null {
  const [recordInfo, setRecordInfo] = useState<RecordInfo | null>(null);
  const [childrenPage, setChildrenPage] = useState(1);
  const [childPosCache] = useState(() => new ChildPosCache());
  const [updateForced, forceUpdate] = useReducer((x) => x + 1, 0);

  const { path } = record;
  useEffect(() => {
    const handler = ({ detail }: CustomEvent<string>) => {
      if (detail === path) {
        forceUpdate();
      }
    };
    subscribe("lektor-attachments-changed", handler);
    return () => unsubscribe("lektor-attachments-changed", handler);
  }, [path]);

  useEffect(() => {
    let ignore = false;

    get("/recordinfo", { path }).then((resp) => {
      if (!ignore) {
        setRecordInfo({ ...resp, alts: resp.alts.sort(compareAlternatives) });
        setChildrenPage(childPosCache.getPosition(path, resp.children.length));
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [path, childPosCache, updateForced]);

  if (!recordInfo) {
    return null;
  }

  return (
    <>
      <PageActions record={record} recordInfo={recordInfo} />
      <Alternatives record={record} page={page} alts={recordInfo.alts} />
      {recordInfo.can_have_children && (
        <ChildActions
          target={page === "preview" ? "preview" : "edit"}
          allChildren={recordInfo.children}
          record={record}
          page={childrenPage}
          setPage={(page) => {
            childPosCache.rememberPosition(record.path, page);
            setChildrenPage(page);
          }}
        />
      )}
      {recordInfo.can_have_attachments && (
        <AttachmentActions record={record} recordInfo={recordInfo} />
      )}
    </>
  );
}

export default Sidebar;
