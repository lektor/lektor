import React from "react";
import { trans } from "../i18n";
import { tokenize, serialize } from "../metaformat";
import { formatUserLabel } from "../userLabel";
import { Field, WidgetProps } from "./mixins";
import {
  getWidgetComponent,
  getWidgetComponentWithFallback,
  FieldBox,
  FieldRows,
} from "../widgets";

type Block = [string, string[]];

function parseFlowFormat(value: string) {
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

function serializeFlowFormat(blocks: Block[]) {
  let rv = [];
  blocks.forEach((block) => {
    const [blockName, lines] = block;
    rv.push("#### " + blockName + " ####\n");
    lines.forEach((line) => {
      rv.push(line.replace(/^(####(.*)####)(\r?\n)?$/, "#$1#$3"));
    });
  });

  rv = rv.join("");

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  if (rv[rv.length - 1] === "\n") {
    rv = rv.substr(0, rv.length - 1);
  }

  return rv;
}

interface FlowBlockModel {
  order: number;
  id: string;
  fields: Field[];
}

function deserializeFlowBlock(
  flowBlockModel: FlowBlockModel,
  lines: string[],
  localId: number
) {
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

  return {
    localId: localId || null,
    flowBlockModel: flowBlockModel,
    data: data,
  };
}

function serializeFlowBlock(flockBlockModel: FlowBlockModel, data) {
  const rv = [];
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
      value = Widget.serializeValue(value, field.type);
    }

    rv.push([field.name, value]);
  });
  return serialize(rv);
}

type FlowWidgetType = {
  collapsed: boolean;
  localId: number;
  flowBlockModel: FlowBlockModel;
}[];

export class FlowWidget extends React.PureComponent<
  WidgetProps<FlowWidgetType>
> {
  static deserializeValue(value, type) {
    let blockId = 0;
    return parseFlowFormat(value).map((item) => {
      const [id, lines] = item;
      const flowBlock = type.flowblocks[id];
      if (flowBlock !== undefined) {
        return deserializeFlowBlock(flowBlock, lines, ++blockId);
      }
      return null;
    });
  }

  static serializeValue(value: FlowWidgetType) {
    return serializeFlowFormat(
      value.map((item) => {
        return [
          item.flowBlockModel.id,
          serializeFlowBlock(item.flowBlockModel, item.data),
        ];
      })
    );
  }

  moveBlock(idx, offset) {
    const newIndex = idx + offset;
    if (newIndex < 0 || newIndex >= this.props.value.length) {
      return;
    }

    const newValue = [...this.props.value];
    newValue[newIndex] = this.props.value[idx];
    newValue[idx] = this.props.value[newIndex];

    this.props.onChange(newValue);
  }

  removeBlock(idx: string) {
    if (confirm(trans("REMOVE_FLOWBLOCK_PROMPT"))) {
      this.props.onChange(this.props.value.filter((item, i) => i !== idx));
    }
  }

  addNewBlock(key) {
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

  toggleBlock(idx) {
    const { collapsed } = this.props.value[idx];
    const newValue = [...this.props.value];
    newValue[idx] = { ...this.props.value[idx], collapsed: !collapsed };
    this.props.onChange(newValue, true); // true => just ui changed
  }

  renderFormField(blockInfo, field: Field, idx: number) {
    const value = blockInfo.data[field.name];
    let placeholder = field.default;
    const Widget = getWidgetComponentWithFallback(field.type);
    if (Widget.deserializeValue && placeholder != null) {
      placeholder = Widget.deserializeValue(placeholder, field.type);
    }

    const onChange = (value) => {
      blockInfo.data[field.name] = value;
      this.props.onChange([...this.props.value]);
    };

    return (
      <FieldBox
        key={idx}
        value={value}
        placeholder={placeholder}
        field={field}
        onChange={onChange}
      />
    );
  }

  renderBlocks() {
    return this.props.value.map((blockInfo, idx) => {
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

      return (
        <div key={blockInfo.localId} className="flow-block">
          <div className="btn-group action-bar">
            <button
              type="button"
              className="btn btn-default btn-xs"
              title={blockInfo.collapsed ? trans("Expand") : trans("Collapse")}
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
              className="btn btn-default btn-xs"
              title={trans("UP")}
              disabled={idx === 0}
              onClick={this.moveBlock.bind(this, idx, -1)}
            >
              <i className="fa fa-fw fa-chevron-up" />
            </button>
            <button
              type="button"
              className="btn btn-default btn-xs"
              title={trans("DOWN")}
              disabled={idx >= this.props.value.length - 1}
              onClick={this.moveBlock.bind(this, idx, 1)}
            >
              <i className="fa fa-fw fa-chevron-down" />
            </button>
            <button
              type="button"
              className="btn btn-default btn-xs"
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
          className="btn btn-default"
          onClick={this.addNewBlock.bind(this, key)}
          title={trans(flowBlockModel.name_i18n)}
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
