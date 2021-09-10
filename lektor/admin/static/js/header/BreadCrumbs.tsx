import React, { useEffect, useState } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";

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
  const urlPath = getUrlRecordPath(path, alt);
  const label = exists ? trans_fallback(item.label_i18n, item.label) : item.id;
  const className = exists
    ? "breadcrumb-item record-crumb"
    : "breadcrumb-item record-crumb missing-record-crumb";
  return (
    <li className={className}>
      <Link to={pathToAdminPage(target, urlPath)}>{label}</Link>
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
      <Link to={pathToAdminPage("add-child", getUrlRecordPath(item.path, alt))}>
        +
      </Link>
    </li>
  ) : null;
}

type Props = Pick<RecordProps, "record" | "page">;

function BreadCrumbs({ record, page }: Props) {
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
          <Link to={pathToAdminPage("edit", "root")}>
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
