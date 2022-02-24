import React from "react";
import { trans, trans_obj } from "../../i18n";
import { NewRecordInfo } from "./types";

/**
 * A field to select one of the available models for the new child page.
 */
export default function AvailableModels({
  newChildInfo,
  selected,
  setSelected,
}: {
  newChildInfo: NewRecordInfo;
  selected: string;
  setSelected: (s: string) => void;
}): JSX.Element {
  const available = Object.values(newChildInfo.available_models).sort((a, b) =>
    a.name.toLowerCase().localeCompare(b.name.toLowerCase())
  );

  return (
    <div className="row field-row">
      <div className="col-md-12">
        <dl className="field">
          <dt>{trans("MODEL")}</dt>
          <dd>
            <select
              value={selected}
              className="form-control"
              onChange={(event) => setSelected(event.target.value)}
            >
              {available.map((model) => (
                <option value={model.id} key={model.id}>
                  {trans_obj(model.name_i18n)}
                </option>
              ))}
            </select>
          </dd>
        </dl>
      </div>
    </div>
  );
}
