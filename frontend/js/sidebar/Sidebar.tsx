import React, { useContext, useEffect, useReducer, useState } from "react";
import { get } from "../fetch";
import { trans_obj } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { Alternative, RecordInfo } from "../components/types";
import PageActions from "./PageActions";
import Alternatives from "./Alternatives";
import AttachmentActions from "./AttachmentActions";
import { CHILDREN_PER_PAGE } from "./constants";
import ChildActions from "./ChildActions";
import { subscribe, unsubscribe } from "../events";
import { PageContext } from "../context/page-context";
import { useRecordPath } from "../context/record-context";

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

function Sidebar(): JSX.Element | null {
  const page = useContext(PageContext);
  const path = useRecordPath();

  const [recordInfo, setRecordInfo] = useState<RecordInfo | null>(null);
  const [childrenPage, setChildrenPage] = useState(1);
  const [childPosCache] = useState(() => new ChildPosCache());
  const [updateForced, forceUpdate] = useReducer((x) => x + 1, 0);

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
      <PageActions recordInfo={recordInfo} />
      <Alternatives alts={recordInfo.alts} />
      {recordInfo.can_have_children && (
        <ChildActions
          targetPage={page === "preview" ? "preview" : "edit"}
          allChildren={recordInfo.children}
          page={childrenPage}
          setPage={(page) => {
            childPosCache.rememberPosition(path, page);
            setChildrenPage(page);
          }}
        />
      )}
      {recordInfo.can_have_attachments && (
        <AttachmentActions recordInfo={recordInfo} />
      )}
    </>
  );
}

export default Sidebar;
