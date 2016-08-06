'use strict'

import React from 'react'
import i18n from '../i18n'
import metaformat from '../metaformat'
import {BasicWidgetMixin} from './mixins'
import userLabel from '../userLabel'


/* circular references require us to do this */
function getWidgetComponent(type) {
  var widgets = require('../widgets');
  return widgets.getWidgetComponent(type);
}

function getWidgets() {
  return require('../widgets');
}


function parseFlowFormat(value) {
  var blocks = [];
  var buf = [];
  var lines = value.split(/\r?\n/);
  var block = null;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];

    // leading whitespace is ignored.
    if (block === null && line.match(/^\s*$/)) {
      continue;
    }

    var blockStart = line.match(/^####\s*([^#]*?)\s*####\s*$/);
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

    buf.push(line.replace(/^#####(.*?)#####$/, '####$1####'));
  }

  if (block !== null) {
    blocks.push([block, buf]);
  }

  return blocks;
}

function serializeFlowFormat(blocks) {
  var rv = [];
  blocks.forEach(function(block) {
    var [blockName, lines] = block;
    rv.push('#### ' + blockName + ' ####\n');
    lines.forEach((line) => {
      rv.push(line.replace(/^(####(.*)####)(\r?\n)?$/, '#$1#$3'));
    });
  });

  rv = rv.join('');

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  if (rv[rv.length - 1] === '\n') {
    rv = rv.substr(0, rv.length - 1);
  }

  return rv;
}

function deserializeFlowBlock(flowBlockModel, lines, localId) {
  var data = {};
  var rawData = {};

  metaformat.tokenize(lines).forEach(function(item) {
    var [key, lines] = item;
    var value = lines.join('');
    rawData[key] = value;
  });

  flowBlockModel.fields.forEach((field) => {
    var value = rawData[field.name] || '';
    var Widget = getWidgetComponent(field.type);
    if (!value && field['default']) {
      value = field['default'];
    }
    if (Widget && Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type);
    }
    data[field.name] = value;
  });

  return {
    localId: localId || null,
    flowBlockModel: flowBlockModel,
    data: data
  }
}

function serializeFlowBlock(flockBlockModel, data) {
  var rv = [];
  flockBlockModel.fields.forEach(function(field) {
    var Widget = getWidgetComponent(field.type);
    if (Widget === null) {
      return;
    }

    var value = data[field.name];
    if (value === undefined || value === null) {
      return;
    }

    if (Widget.serializeValue) {
      value = Widget.serializeValue(value, field.type);
    }

    rv.push([field.name, value]);
  });
  return metaformat.serialize(rv);
}

// ever growing counter of block ids.  Good enough for what we do I think.
var lastBlockId = 0;


var FlowWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: function(value, type) {
      return parseFlowFormat(value).map(function(item) {
        var [id, lines] = item;
        var flowBlock = type.flowblocks[id];
        if (flowBlock !== undefined) {
          return deserializeFlowBlock(flowBlock, lines, ++lastBlockId);
        }
        return null;
      }.bind(this));
    },

    serializeValue: function(value) {
      return serializeFlowFormat(value.map(function(item) {
        return [
          item.flowBlockModel.id,
          serializeFlowBlock(item.flowBlockModel, item.data)
        ];
      }));
    }
  },

  // XXX: the modification of props is questionable

  moveBlock: function(idx, offset, event) {
    event.preventDefault();

    var newIndex = idx + offset;
    if (newIndex < 0 || newIndex >= this.props.value.length) {
      return;
    }

    var tmp = this.props.value[newIndex];
    this.props.value[newIndex] = this.props.value[idx];
    this.props.value[idx] = tmp;

    if (this.props.onChange) {
      this.props.onChange(this.props.value);
    }
  },

  removeBlock: function(idx, event) {
    event.preventDefault();

    if (confirm(i18n.trans('REMOVE_FLOWBLOCK_PROMPT'))) {
      this.props.value.splice(idx, 1);
      if (this.props.onChange) {
        this.props.onChange(this.props.value);
      }
    }
  },

  addNewBlock: function(key, event) {
    event.preventDefault();

    var flowBlockModel = this.props.type.flowblocks[key];

    // this is a rather ugly way to do this, but hey, it works.
    this.props.value.push(deserializeFlowBlock(flowBlockModel, [],
                                               ++lastBlockId));
    if (this.props.onChange) {
      this.props.onChange(this.props.value);
    }
  },

  renderFormField: function(blockInfo, field, idx) {
    var widgets = getWidgets();
    var value = blockInfo.data[field.name];
    var placeholder = field['default'];
    var Widget = widgets.getWidgetComponentWithFallback(field.type);
    if (Widget.deserializeValue && placeholder != null) {
      placeholder = Widget.deserializeValue(placeholder, field.type);
    }

    var onChange = !this.props.onChange ? null : (value) => {
      blockInfo.data[field.name] = value;
      this.props.onChange(this.props.value);
    };

    return (
      <widgets.FieldBox
        key={idx}
        value={value}
        placeholder={placeholder}
        field={field}
        onChange={onChange}
      />
    );
  },

  renderBlocks: function() {
    var widgets = getWidgets();

    return this.props.value.map((blockInfo, idx) => {
      // bad block is no block
      if (blockInfo === null) {
        return null;
      }

      var fields = widgets.renderFieldRows(
        blockInfo.flowBlockModel.fields,
        null,
        this.renderFormField.bind(this, blockInfo)
      );

      return (
        <div key={blockInfo.localId} className="flow-block">
          <div className="btn-group action-bar">
            <button
              className="btn btn-default btn-xs"
              title={i18n.trans('UP')}
              disabled={idx == 0}
              onClick={this.moveBlock.bind(this, idx, -1)}>
              <i className="fa fa-fw fa-chevron-up"></i>
            </button>
            <button
              className="btn btn-default btn-xs"
              title={i18n.trans('DOWN')}
              disabled={idx >= this.props.value.length - 1}
              onClick={this.moveBlock.bind(this, idx, 1)}>
              <i className="fa fa-fw fa-chevron-down"></i>
            </button>
            <button
              className="btn btn-default btn-xs"
              title={i18n.trans('REMOVE')}
              onClick={this.removeBlock.bind(this, idx)}>
              <i className="fa fa-fw fa-times"></i>
            </button>
          </div>
          <h4 className="block-name">{userLabel.format(blockInfo.flowBlockModel.name_i18n)}</h4>
          {fields}
        </div>
      );
    });
  },

  renderAddBlockSection: function() {
    var choices = [];

    this.props.type.flowblock_order.forEach((key) => {
      let flowBlockModel = this.props.type.flowblocks[key];
      let label = flowBlockModel.button_label
        ? userLabel.format(flowBlockModel.button_label)
        : userLabel.format(flowBlockModel.name_i18n);
      choices.push([flowBlockModel.id, label, i18n.trans(flowBlockModel.name_i18n)]);
    });

    var buttons = choices.map((item) => {
      var [key, label, title] = item;
      return (
        <button
          className="btn btn-default"
          onClick={this.addNewBlock.bind(this, key)}
          title={title}
          key={key}>{label}</button>
      );
    });

    return (
      <div className="add-block">
        <label>{i18n.trans('ADD_FLOWBLOCK') + ': '}</label>
        <div className="btn-group">
          {buttons}
        </div>
      </div>
    );
  },

  render: function() {
    var {className, value, type, ...otherProps} = this.props;
    className = (className || '') + ' flow';

    return (
      <div className={className}>
        {this.renderBlocks()}
        {this.renderAddBlockSection()}
      </div>
    );
  }
});

export default {
  FlowWidget: FlowWidget
}
