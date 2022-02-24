import React from "react";
import { trans, trans_obj } from "../../i18n";
import { formatUserLabel } from "../../userLabel";
import { FlowBlockModel } from "./FlowWidget";

export default function AddFlowBlockButtons({
  flowblock_order,
  flowblocks,
  addBlock,
}: {
  flowblocks: Record<string, FlowBlockModel>;
  flowblock_order: string[];
  addBlock: (model: FlowBlockModel) => void;
}): JSX.Element {
  const models = flowblock_order.map((key) => flowblocks[key]);
  return (
    <div className="add-flow-block">
      <label>{`${trans("ADD_FLOWBLOCK")}: `}</label>
      <div className="btn-group">
        {models.map((model) => {
          const label = model.button_label
            ? formatUserLabel(model.button_label)
            : formatUserLabel(model.name_i18n);
          return (
            <button
              type="button"
              className="btn btn-secondary border"
              onClick={() => addBlock(model)}
              title={trans_obj(model.name_i18n)}
              key={model.id}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
