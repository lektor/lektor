import React from "react";
import { Result } from "./FindFiles";

/**
 * A page in the result list in the find files dialog.
 */
export default function ResultRow({
  result,
  isActive,
  onClick,
  onMouseEnter,
}: {
  result: Result;
  isActive: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}): JSX.Element {
  return (
    <li
      className={isActive ? "active" : ""}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
    >
      {result.parents.map((item, idx) => (
        <span className="parent" key={idx}>
          {item.title}
        </span>
      ))}
      <strong>{result.title}</strong>
    </li>
  );
}
