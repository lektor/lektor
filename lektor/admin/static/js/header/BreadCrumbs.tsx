import React, { useEffect, useState } from "react";
import { RecordProps } from "../components/RecordComponent";
import Link from "../components/Link";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { adminPath } from "../components/use-go-to-admin-page";

interface RecordPathInfoSegment {
  id: string;
  path: string;
  label: string;
  label_i18n?: Record<string, string>;
  exists: boolean;
  can_have_children: boolean;
}

function Crumb({
  alt,
  item,
  target,
}: {
  alt: string;
  item: RecordPathInfoSegment;
  target: "preview" | "edit";
}) {
  const { path, exists } = item;
  const label = exists ? trans_fallback(item.label_i18n, item.label) : item.id;
  const className = exists
    ? "breadcrumb-item record-crumb"
    : "breadcrumb-item record-crumb missing-record-crumb";
  return (
    <li className={className}>
      <Link to={adminPath(target, path, alt)}>{label}</Link>
    </li>
  );
}

function AddNewPage({
  alt,
  item,
}: {
  alt: string;
  item: RecordPathInfoSegment;
}) {
  return item.can_have_children ? (
    <li className="new-record-crumb">
      <Link to={adminPath("add-child", item.path, alt)}>+</Link>
    </li>
  ) : null;
}

function BreadCrumbs({ record, page }: RecordProps): JSX.Element {
  const [segments, setSegments] = useState<RecordPathInfoSegment[] | null>(
    null
  );
  const { alt, path } = record;

  useEffect(() => {
    let ignore = false;

    loadData("/pathinfo", { path }).then(
      (resp: { segments: RecordPathInfoSegment[] }) => {
        if (!ignore) {
          setSegments(resp.segments);
        }
      },
      showErrorDialog
    );

    return () => {
      ignore = true;
    };
  }, [path]);

  if (!segments) {
    return (
      <ul className="breadcrumb">
        <li>
          <Link to={adminPath("edit", "/", "_primary")}>
            {trans("BACK_TO_OVERVIEW")}
          </Link>
        </li>
      </ul>
    );
  }

  const target = page === "preview" ? "preview" : "edit";
  const lastItem = segments[segments.length - 1];

  return (
    <ul className="breadcrumb">
      {segments.map((item) => (
        <Crumb key={item.path} item={item} alt={alt} target={target} />
      ))}
      <AddNewPage item={lastItem} alt={alt} />
    </ul>
  );
}

export default BreadCrumbs;
