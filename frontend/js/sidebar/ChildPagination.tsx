import React from "react";
import { CHILDREN_PER_PAGE } from "./constants";

/** Pagination buttons for the list of children in the sidebar. */
export default function ChildPagination({
  page,
  numberOfChildren,
  setPage,
}: {
  page: number;
  numberOfChildren: number;
  setPage: (n: number) => void;
}): JSX.Element | null {
  const pages = Math.ceil(numberOfChildren / CHILDREN_PER_PAGE);
  if (pages <= 1) {
    return null;
  }
  return (
    <li className="pagination">
      {page > 1 ? (
        <a
          href="#"
          onClick={(ev) => {
            ev.preventDefault();
            setPage(page - 1);
          }}
        >
          «
        </a>
      ) : (
        <em>«</em>
      )}
      <span className="page">{page + " / " + pages}</span>
      {page < pages ? (
        <a
          href="#"
          onClick={(ev) => {
            ev.preventDefault();
            setPage(page + 1);
          }}
        >
          »
        </a>
      ) : (
        <em>»</em>
      )}
    </li>
  );
}
