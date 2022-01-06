import React from "react";
import { adminPath } from "../../components/use-go-to-admin-page";
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
  alt: string;
  target: string;
}): JSX.Element {
  return (
    <li className={isActive ? "active" : ""}>
      <a href={adminPath(target, result.path, alt)} onClick={dismiss}>
        {result.parents.map((item, idx) => (
          <span key={idx}>{item.title}</span>
        ))}
        <strong>{result.title}</strong>
      </a>
    </li>
  );
}
