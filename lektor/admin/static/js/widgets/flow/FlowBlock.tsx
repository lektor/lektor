import React, { memo, useReducer } from "react";
import { trans } from "../../i18n";
import { formatUserLabel } from "../../userLabel";
import { Field } from "../types";
import { FieldRows } from "../../widgets";
import { FlowBlockData } from "./FlowWidget";

/**
 * Render a single flow block in the flow widget. The function to render
 * the child input widgets is passed down.
 */
export default memo(function FlowBlock({
  block,
  moveBlock,
  renderFormField,
  removeBlock,
  idx,
  length,
}: {
  block: FlowBlockData;
  moveBlock: (i: number, s: number) => void;
  renderFormField: (b: FlowBlockData, f: Field) => JSX.Element;
  removeBlock: (i: number) => void;
  idx: number;
  length: number;
}) {
  const [collapsed, toggle] = useReducer((s) => !s, false);
  return (
    <div className="flow-block">
      <div className="d-flex justify-content-between">
        <h4 className="block-name">{formatUserLabel(block.model.name_i18n)}</h4>
        <div className="btn-group action-bar">
          <button
            type="button"
            className="btn btn-secondary btn-sm border"
            title={collapsed ? trans("EXPAND") : trans("COLLAPSE")}
            onClick={toggle}
          >
            <i className={collapsed ? "fa fa-expand" : "fa fa-compress"} />
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm border"
            title={trans("UP")}
            disabled={idx === 0}
            onClick={() => moveBlock(idx, -1)}
          >
            <i className="fa fa-fw fa-chevron-up" />
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm border"
            title={trans("DOWN")}
            disabled={idx === length - 1}
            onClick={() => moveBlock(idx, 1)}
          >
            <i className="fa fa-fw fa-chevron-down" />
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm border"
            title={trans("REMOVE")}
            onClick={() => removeBlock(idx)}
          >
            <i className="fa fa-fw fa-times" />
          </button>
        </div>
      </div>
      {collapsed ? null : (
        <FieldRows
          fields={block.model.fields}
          renderFunc={renderFormField.bind(undefined, block)}
        />
      )}
    </div>
  );
});
