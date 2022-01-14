import React, { SetStateAction, useCallback } from "react";
import { trans, Translatable } from "../../i18n";
import { tokenize, serialize } from "./metaformat";
import { Field, BaseWidgetType, WidgetProps } from "../types";
import {
  getWidgetComponent,
  getWidgetComponentWithFallback,
  FieldBox,
} from "../../widgets";
import FlowBlock from "./FlowBlock";
import AddFlowBlockButtons from "./AddFlowBlockButtons";

type Block = [name: string, lines: string[]];

/**
 * Parse the row string from a Lektor file for the flow format
 * to its separate flow blocks. Each flow block can then be
 * deserialised with deserializeFlowBlock.
 */
export function parseFlowFormat(value = ""): Block[] {
  const blocks: Block[] = [];
  const lines = value.split(/\r?\n/);
  let blockName: string | null = null;
  let blockLines: string[] = [];

  const flush = () => {
    if (blockName !== null) {
      blocks.push([blockName, blockLines]);
      blockLines = [];
    }
  };

  for (const line of lines) {
    // leading whitespace is ignored.
    if (blockName === null && line.match(/^\s*$/)) {
      continue;
    }

    const blockStart = line.match(/^####\s*([^#]*?)\s*####\s*$/);
    if (!blockStart) {
      if (blockName === null) {
        // bad format :(
        return [];
      }
    } else {
      flush();
      blockName = blockStart[1];
      continue;
    }

    blockLines.push(line.replace(/^#####(.*?)#####$/, "####$1####"));
  }

  flush();
  return blocks;
}

/** Serialise an array of single blocks to a string. */
export function serializeFlowFormat(blocks: Block[]): string {
  const serialisedBlocks: string[] = [];
  blocks.forEach(([blockName, lines]) => {
    serialisedBlocks.push(`#### ${blockName} ####\n`);
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

export interface FlowBlockModel {
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

export interface FlowBlockData {
  /** The current data for this flow block. */
  data: Record<string, string>;
  /** The data model of the flow block. */
  model: FlowBlockModel;
  /** A key to identify this item to React (needed when moving them up/down). */
  localId: number;
}

function deserializeFlowBlock(
  model: FlowBlockModel,
  lines: string[],
  localId: number
): FlowBlockData {
  const data: Record<string, string> = {};
  const rawData: Record<string, string> = {};

  tokenize(lines).forEach(([key, lines]) => {
    rawData[key] = lines.join("");
  });

  model.fields.forEach((field) => {
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

  return { localId, model, data };
}

function serializeFlowBlock(
  flockBlockModel: FlowBlockModel,
  data: Record<string, string>
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
      value = Widget.serializeValue(value, field.type);
    }
    rv.push([field.name, value]);
  });
  return serialize(rv);
}

export function FlowWidget(
  props: WidgetProps<readonly FlowBlockData[], FlowBlockWidgetType>
): JSX.Element {
  const { value, onChange } = props;

  const moveBlock = useCallback(
    (idx: number, offset: number) => {
      onChange((prevValue) => {
        const newIndex = idx + offset;
        if (newIndex < 0 || newIndex >= prevValue.length) {
          return prevValue;
        }

        const newValue = [...prevValue];
        newValue[newIndex] = prevValue[idx];
        newValue[idx] = prevValue[newIndex];
        return newValue;
      });
    },
    [onChange]
  );

  const removeBlock = useCallback(
    (idx: number) => {
      if (confirm(trans("REMOVE_FLOWBLOCK_PROMPT"))) {
        onChange((v) => v.filter((item, i) => i !== idx));
      }
    },
    [onChange]
  );

  const addNewBlock = useCallback(
    (flowBlockModel: FlowBlockModel) => {
      onChange((prevValue) => {
        // find the first available id for this new block - use findMax + 1
        const newBlockId =
          Math.max(0, ...prevValue.map(({ localId }) => localId)) + 1;
        // this is a rather ugly way to do this, but hey, it works.
        const newBlock = deserializeFlowBlock(flowBlockModel, [], newBlockId);
        return [...prevValue, newBlock];
      });
    },
    [onChange]
  );

  const renderFormField = useCallback(
    (block: FlowBlockData, field: Field) => {
      const fieldValue = block.data[field.name];
      let placeholder = field.default;
      const Widget = getWidgetComponentWithFallback(field.type);
      if (Widget.deserializeValue && placeholder != null) {
        placeholder = Widget.deserializeValue(placeholder, field.type);
      }

      const setFieldValue = (fieldName: string, v: SetStateAction<string>) => {
        onChange((prevValue) => {
          const newValue = [...prevValue];
          const idx = newValue.indexOf(block);
          const data = {
            ...block.data,
            [fieldName]: typeof v === "function" ? v(block.data[fieldName]) : v,
          };
          newValue[idx] = { ...block, data };
          return newValue;
        });
      };

      return (
        <FieldBox
          key={field.name}
          value={fieldValue}
          placeholder={placeholder}
          field={field}
          setFieldValue={setFieldValue}
        />
      );
    },
    [onChange]
  );

  const { flowblock_order, flowblocks } = props.type;
  return (
    <div className="flow-widget">
      {value.map((block, idx) => (
        <FlowBlock
          key={block.localId}
          block={block}
          moveBlock={moveBlock}
          renderFormField={renderFormField}
          removeBlock={removeBlock}
          length={value.length}
          idx={idx}
        />
      ))}
      <AddFlowBlockButtons
        flowblock_order={flowblock_order}
        flowblocks={flowblocks}
        addBlock={addNewBlock}
      />
    </div>
  );
}

FlowWidget.deserializeValue = (
  value: string,
  { flowblocks }: FlowBlockWidgetType
): FlowBlockData[] => {
  let blockId = 0;
  const blocks: FlowBlockData[] = [];
  parseFlowFormat(value).forEach(([id, lines]) => {
    const flowBlock = flowblocks[id];
    if (flowBlock !== undefined) {
      blocks.push(deserializeFlowBlock(flowBlock, lines, ++blockId));
    }
  });
  return blocks;
};

FlowWidget.serializeValue = (value: FlowBlockData[]) => {
  return serializeFlowFormat(
    value.map(({ model: flowBlockModel, data }) => [
      flowBlockModel.id,
      serializeFlowBlock(flowBlockModel, data),
    ])
  );
};
