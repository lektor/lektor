import React from "react";
import { trans, Translatable, trans_obj } from "../i18n";
import { tokenize, serialize } from "../metaformat";
import { formatUserLabel } from "../userLabel";
import { Field, BaseWidgetType, WidgetProps } from "./types";
import {
  getWidgetComponent,
  getWidgetComponentWithFallback,
  FieldBox,
  FieldRows,
} from "../widgets";

type Block = [string, string[]];

export function parseFlowFormat(value: string): Block[] | null {
  const blocks: Block[] = [];
  let buf = [];
  const lines = value.split(/\r?\n/);
  let block = null;

  for (const line of lines) {
    // leading whitespace is ignored.
    if (block === null && line.match(/^\s*$/)) {
      continue;
    }

    const blockStart = line.match(/^####\s*([^#]*?)\s*####\s*$/);
    if (!blockStart) {
      if (block === null) {
        // bad format :(
        return null;
      }
    } else {
      if (block !== null) {
        blocks.push([block, buf]);
        buf = [];
      }
      block = blockStart[1];
      continue;
    }

    buf.push(line.replace(/^#####(.*?)#####$/, "####$1####"));
  }

  if (block !== null) {
    blocks.push([block, buf]);
  }

  return blocks;
}

export function serializeFlowFormat(blocks: Block[]): string {
  const serialisedBlocks: string[] = [];
  blocks.forEach(([blockName, lines]) => {
    serialisedBlocks.push("#### " + blockName + " ####\n");
    lines.forEach((line) => {
      serialisedBlocks.push(line.replace(/^(####(.*)####)(\r?\n)?$/, "#$1#$3"));
    });
  });

  const rv = serialisedBlocks.join("");

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  return rv[rv.length - 1] === "\n" ? rv.substr(0, rv.length - 1) : rv;
}

interface FlowBlockModel {
  order: number;
  id: string;
  fields: Field[];
  name: string;
  name_i18n: Translatable;
  button_label?: string;
}

export interface FlowBlockWidgetType extends BaseWidgetType {
  widget: "flow";
  flowblock_order: string[];
  flowblocks: Record<string, FlowBlockModel>;
}

interface FlowBlock {
  data: Record<string, unknown>;
  flowBlockModel: FlowBlockModel;
  localId: number;
  collapsed: boolean;
}

function deserializeFlowBlock(
  flowBlockModel: FlowBlockModel,
  lines: string[],
  localId: number
): FlowBlock {
  const data: Record<string, unknown> = {};
  const rawData: Record<string, string> = {};

  tokenize(lines).forEach((item) => {
    const [key, lines] = item;
    const value = lines.join("");
    rawData[key] = value;
  });

  flowBlockModel.fields.forEach((field) => {
    let value = rawData[field.name] || "";
    const Widget = getWidgetComponent(field.type);
    if (!value && field.default) {
      value = field.default;
    }
    if (Widget && Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type);
    }
    data[field.name] = value;
  });

  return { localId, flowBlockModel, data, collapsed: false };
}

function serializeFlowBlock(
  flockBlockModel: FlowBlockModel,
  data: Record<string, unknown>
) {
  const rv: [string, string][] = [];
  flockBlockModel.fields.forEach((field) => {
    const Widget = getWidgetComponent(field.type);
    if (Widget === null) {
      return;
    }

    let value = data[field.name];
    if (value === undefined || value === null) {
      return;
    }

    if (Widget.serializeValue) {
      // @ts-expect-error The data record is not properly typed yet
      value = Widget.serializeValue(value, field.type);
    }

    // @ts-expect-error The data record is not properly typed yet
    rv.push([field.name, value]);
  });
  return serialize(rv);
}

export class FlowWidget extends React.PureComponent<
  WidgetProps<FlowBlock[], FlowBlockWidgetType>
> {
  static deserializeValue(
    value: string,
    type: FlowBlockWidgetType
  ): (FlowBlock | null)[] {
    let blockId = 0;
    return (parseFlowFormat(value) ?? []).map((item) => {
      const [id, lines] = item;
      const flowBlock = type.flowblocks[id];
      if (flowBlock !== undefined) {
        return deserializeFlowBlock(flowBlock, lines, ++blockId);
      }
      return null;
    });
  }

  static serializeValue(value: FlowBlock[]) {
    return serializeFlowFormat(
      value.map((item) => {
        return [
          item.flowBlockModel.id,
          serializeFlowBlock(item.flowBlockModel, item.data),
        ];
      })
    );
  }

  moveBlock(idx: number, offset: number) {
    if (this.props.value) {
      const newIndex = idx + offset;
      if (newIndex < 0 || newIndex >= this.props.value.length) {
        return;
      }

      const newValue = [...this.props.value];
      newValue[newIndex] = this.props.value[idx];
      newValue[idx] = this.props.value[newIndex];

      this.props.onChange(newValue);
    }
  }

  removeBlock(idx: number) {
    if (this.props.value) {
      if (confirm(trans("REMOVE_FLOWBLOCK_PROMPT"))) {
        this.props.onChange(this.props.value.filter((item, i) => i !== idx));
      }
    }
  }

  addNewBlock(key: string) {
    if (this.props.value) {
      const flowBlockModel = this.props.type.flowblocks[key];

      // find the first available id for this new block - use findMax + 1
      const blockIds = this.props.value.map((block) => block.localId);
      const newBlockId = blockIds.length === 0 ? 1 : Math.max(...blockIds) + 1;

      // this is a rather ugly way to do this, but hey, it works.
      const newValue = [
        ...this.props.value,
        deserializeFlowBlock(flowBlockModel, [], newBlockId),
      ];
      this.props.onChange(newValue);
    }
  }

  toggleBlock(idx: number) {
    if (this.props.value) {
      const { collapsed } = this.props.value[idx];
      const newValue = [...this.props.value];
      newValue[idx] = { ...this.props.value[idx], collapsed: !collapsed };
      this.props.onChange(newValue, true); // true => just ui changed
    }
  }

  renderFormField(blockInfo: FlowBlock, field: Field, idx: number) {
    if (this.props.value) {
      // @ts-expect-error The data record is not properly typed yet
      const value: string = blockInfo.data[field.name];
      let placeholder = field.default;
      const Widget = getWidgetComponentWithFallback(field.type);
      if (Widget.deserializeValue && placeholder != null) {
        placeholder = Widget.deserializeValue(placeholder, field.type);
      }

      const setFieldValue = (field: Field, value: unknown) => {
        blockInfo.data[field.name] = value;

        // @ts-expect-error The data record is not properly typed yet
        this.props.onChange([...this.props.value]);
      };

      return (
        <FieldBox
          key={idx}
          value={value}
          placeholder={placeholder}
          field={field}
          setFieldValue={setFieldValue}
        />
      );
    }
  }

  renderBlocks() {
    const flowBlocks = this.props.value ?? [];
    return flowBlocks.map((blockInfo, idx) => {
      // bad block is no block
      if (blockInfo === null) {
        return null;
      }

      const fields = blockInfo.collapsed ? null : (
        <FieldRows
          fields={blockInfo.flowBlockModel.fields}
          renderFunc={this.renderFormField.bind(this, blockInfo)}
        />
      );
      const buttonClass = "btn btn-secondary btn-sm border";

      return (
        <div key={blockInfo.localId} className="flow-block">
          <div className="btn-group action-bar">
            <button
              type="button"
              className={buttonClass}
              title={blockInfo.collapsed ? trans("EXPAND") : trans("COLLAPSE")}
              onClick={this.toggleBlock.bind(this, idx)}
            >
              <i
                className={
                  blockInfo.collapsed ? "fa fa-expand" : "fa fa-compress"
                }
              />
            </button>
            <button
              type="button"
              className={buttonClass}
              title={trans("UP")}
              disabled={idx === 0}
              onClick={this.moveBlock.bind(this, idx, -1)}
            >
              <i className="fa fa-fw fa-chevron-up" />
            </button>
            <button
              type="button"
              className={buttonClass}
              title={trans("DOWN")}
              disabled={idx >= flowBlocks.length - 1}
              onClick={this.moveBlock.bind(this, idx, 1)}
            >
              <i className="fa fa-fw fa-chevron-down" />
            </button>
            <button
              type="button"
              className={buttonClass}
              title={trans("REMOVE")}
              onClick={this.removeBlock.bind(this, idx)}
            >
              <i className="fa fa-fw fa-times" />
            </button>
          </div>
          <h4 className="block-name">
            {formatUserLabel(blockInfo.flowBlockModel.name_i18n)}
          </h4>
          {fields}
        </div>
      );
    });
  }

  render() {
    const addBlockButtons = this.props.type.flowblock_order.map((key) => {
      const flowBlockModel = this.props.type.flowblocks[key];
      const label = flowBlockModel.button_label
        ? formatUserLabel(flowBlockModel.button_label)
        : formatUserLabel(flowBlockModel.name_i18n);
      return (
        <button
          type="button"
          className="btn btn-secondary border"
          onClick={this.addNewBlock.bind(this, key)}
          title={trans_obj(flowBlockModel.name_i18n)}
          key={flowBlockModel.id}
        >
          {label}
        </button>
      );
    });

    return (
      <div className="flow">
        {this.renderBlocks()}
        <div className="add-flow-block">
          <label>{trans("ADD_FLOWBLOCK") + ": "}</label>
          <div className="btn-group">{addBlockButtons}</div>
        </div>
      </div>
    );
  }
}
