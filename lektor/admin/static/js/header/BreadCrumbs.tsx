import React, { useEffect, useState } from "react";
import { RecordProps } from "../components/RecordComponent";
import { get } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import AdminLink from "../components/AdminLink";

export interface RecordPathInfoSegment {
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
    ? "breadcrumb-item"
    : "breadcrumb-item missing-record-crumb";
  return (
    <li className={className}>
      <AdminLink page={target} path={path} alt={alt}>
        {label}
      </AdminLink>
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
      <AdminLink page={"add-child"} path={item.path} alt={alt}>
        +
      </AdminLink>
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

    get("/pathinfo", { path }).then((resp) => {
      if (!ignore) {
        setSegments(resp.segments);
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [path]);

  if (!segments) {
    return (
      <ul className="breadcrumb">
        <li>
          <AdminLink page="edit" path="/" alt="_primary">
            {trans("BACK_TO_OVERVIEW")}
          </AdminLink>
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
