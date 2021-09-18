import React from "react";
import { trans } from "../../i18n";
import { formatUserLabel } from "../../userLabel";
import { SlugInputWidget } from "../../widgets/SlugInputWidget";

/**
 * Slug for the new child page.
 */
export default function Slug({
  id,
  placeholder,
  setId,
}: {
  id: string;
  placeholder: string;
  setId: (s: string) => void;
}): JSX.Element {
  return (
    <div className="row field-row">
      <div className="col-md-12">
        <dl className="field">
          <dt>{formatUserLabel(trans("ID"))}</dt>
          <dd>
            <SlugInputWidget
              value={id}
              placeholder={placeholder}
              onChange={setId}
              type={{ widget: "slug", name: "slug", size: "normal" }}
            />
          </dd>
        </dl>
      </div>
    </div>
  );
}
