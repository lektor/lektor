import React from "react";
import { trans, trans_obj } from "../i18n";
import { useRecordAlt } from "../context/record-context";
import { RecordChild } from "../components/types";
import ChildPagination from "./ChildPagination";
import { CHILDREN_PER_PAGE } from "./constants";
import AdminLink from "../components/AdminLink";

export default function ChildActions({
  targetPage,
  allChildren,
  page,
  setPage,
}: {
  targetPage: "preview" | "edit";
  allChildren: RecordChild[];
  page: number;
  setPage: (n: number) => void;
}): JSX.Element {
  const alt = useRecordAlt();

  const shownChildren = allChildren.slice(
    (page - 1) * CHILDREN_PER_PAGE,
    page * CHILDREN_PER_PAGE
  );

  return (
    <>
      <h3>{trans("CHILD_PAGES")}</h3>
      <ul className="nav">
        <ChildPagination
          numberOfChildren={allChildren.length}
          page={page}
          setPage={setPage}
        />
        {shownChildren.length > 0 ? (
          shownChildren.map((child) => (
            <li key={child.id}>
              <AdminLink page={targetPage} path={child.path} alt={alt}>
                {trans_obj(child.label_i18n)}
              </AdminLink>
            </li>
          ))
        ) : (
          <li key="_missing">
            <em>{trans("NO_CHILD_PAGES")}</em>
          </li>
        )}
      </ul>
    </>
  );
}
