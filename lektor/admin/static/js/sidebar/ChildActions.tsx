import React from "react";
import { trans, trans_obj } from "../i18n";
import {
  getUrlRecordPath,
  RecordPathDetails,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordChild } from "../components/types";
import ChildPagination from "./ChildPagination";
import { CHILDREN_PER_PAGE } from "./constants";

export default function ChildActions({
  target,
  allChildren,
  record,
  page,
  setPage,
}: {
  target: "preview" | "edit";
  allChildren: RecordChild[];
  record: RecordPathDetails;
  page: number;
  setPage: (n: number) => void;
}): JSX.Element {
  const shownChildren = allChildren.slice(
    (page - 1) * CHILDREN_PER_PAGE,
    page * CHILDREN_PER_PAGE
  );

  return (
    <div key="children" className="section">
      <h3>{trans("CHILD_PAGES")}</h3>
      <ul className="nav record-children">
        <ChildPagination
          numberOfChildren={allChildren.length}
          page={page}
          setPage={setPage}
        />
        {shownChildren.length > 0 ? (
          shownChildren.map((child) => (
            <li key={child.id}>
              <Link
                to={`${getUrlRecordPath(child.path, record.alt)}/${target}`}
              >
                {trans_obj(child.label_i18n)}
              </Link>
            </li>
          ))
        ) : (
          <li key="_missing">
            <em>{trans("NO_CHILD_PAGES")}</em>
          </li>
        )}
      </ul>
    </div>
  );
}
