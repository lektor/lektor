import React from "react";
import AdminLink from "../../components/AdminLink";
import { PageName } from "../../context/page-context";
import { RecordAlternative } from "../../context/record-context";
import { SearchResult } from "./FindFiles";

/**
 * A page in the result list in the find files dialog.
 */
export default function ResultRow({
  result,
  isActive,
  dismiss,
  alt,
  target,
}: {
  result: SearchResult;
  isActive: boolean;
  dismiss: () => void;
  alt: RecordAlternative;
  target: PageName;
}): JSX.Element {
  return (
    <li className={isActive ? "active" : ""}>
      <AdminLink page={target} path={result.path} alt={alt} onClick={dismiss}>
        {result.parents.map((item) => (
          <span key={item.title}>{item.title}</span>
        ))}
        <strong>{result.title}</strong>
      </AdminLink>
    </li>
  );
}
