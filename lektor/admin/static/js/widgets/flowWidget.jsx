'use strict'

/* eslint-env browser */

import React from 'react'
import i18n from '../i18n'
import metaformat from '../metaformat'
import {BasicWidgetMixin} from './mixins'
import userLabel from '../userLabel'
import widgets from '../widgets'

/* circular references require us to do this */
const getWidgetComponent = (type) => {
  return widgets.getWidgetComponent(type)
}

const getWidgets = () => {
  return widgets
}

const parseFlowFormat = (value) => {
  let blocks = []
  let buf = []
  let lines = value.split(/\r?\n/)
  let block = null

  for (const line of lines) {
    // leading whitespace is ignored.
    if (block === null && line.match(/^\s*$/)) {
      continue
    }

    const blockStart = line.match(/^####\s*([^#]*?)\s*####\s*$/)
    if (!blockStart) {
      if (block === null) {
        // bad format :(
        return null
      }
    } else {
      if (block !== null) {
        blocks.push([block, buf])
        buf = []
      }
      block = blockStart[1]
      continue
    }

    buf.push(line.replace(/^#####(.*?)#####$/, '####$1####'))
  }

  if (block !== null) {
    blocks.push([block, buf])
  }

  return blocks
}

const serializeFlowFormat = (blocks) => {
  let rv = []
  blocks.forEach((block) => {
    const [blockName, lines] = block
    rv.push('#### ' + blockName + ' ####\n')
    lines.forEach((line) => {
      rv.push(line.replace(/^(####(.*)####)(\r?\n)?$/, '#$1#$3'))
    })
  })

  rv = rv.join('')

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  if (rv[rv.length - 1] === '\n') {
    rv = rv.substr(0, rv.length - 1)
  }

  return rv
}

const deserializeFlowBlock = (flowBlockModel, lines, localId) => {
  let data = {}
  let rawData = {}

  metaformat.tokenize(lines).forEach((item) => {
    const [key, lines] = item
    const value = lines.join('')
    rawData[key] = value
  })

  flowBlockModel.fields.forEach((field) => {
    let value = rawData[field.name] || ''
    const Widget = getWidgetComponent(field.type)
    if (!value && field['default']) {
      value = field['default']
    }
    if (Widget && Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type)
    }
    data[field.name] = value
  })

  return {
    localId: localId || null,
    flowBlockModel: flowBlockModel,
    data: data
  }
}

const serializeFlowBlock = (flockBlockModel, data) => {
  let rv = []
  flockBlockModel.fields.forEach((field) => {
    const Widget = getWidgetComponent(field.type)
    if (Widget === null) {
      return
    }

    let value = data[field.name]
    if (value === undefined || value === null) {
      return
    }

    if (Widget.serializeValue) {
      value = Widget.serializeValue(value, field.type)
    }

    rv.push([field.name, value])
  })
  return metaformat.serialize(rv)
}

// ever growing counter of block ids.  Good enough for what we do I think.
let lastBlockId = 0

const FlowWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: (value, type) => {
      return parseFlowFormat(value).map((item) => {
        const [id, lines] = item
        const flowBlock = type.flowblocks[id]
        if (flowBlock !== undefined) {
          return deserializeFlowBlock(flowBlock, lines, ++lastBlockId)
        }
        return null
      })
    },

    serializeValue: (value) => {
      return serializeFlowFormat(value.map((item) => {
        return [
          item.flowBlockModel.id,
          serializeFlowBlock(item.flowBlockModel, item.data)
        ]
      }))
    }
  },

  // XXX: the modification of props is questionable

  moveBlock: function (idx, offset, event) {
    event.preventDefault()

    const newIndex = idx + offset
    if (newIndex < 0 || newIndex >= this.props.value.length) {
      return
    }

    const tmp = this.props.value[newIndex]
    this.props.value[newIndex] = this.props.value[idx]
    this.props.value[idx] = tmp

    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  },

  removeBlock: function (idx, event) {
    event.preventDefault()

    if (confirm(i18n.trans('REMOVE_FLOWBLOCK_PROMPT'))) {
      this.props.value.splice(idx, 1)
      if (this.props.onChange) {
        this.props.onChange(this.props.value)
      }
    }
  },

  addNewBlock: function (key, event) {
    event.preventDefault()

    const flowBlockModel = this.props.type.flowblocks[key]

    // this is a rather ugly way to do this, but hey, it works.
    this.props.value.push(deserializeFlowBlock(flowBlockModel, [],
                                               ++lastBlockId))
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  },

  renderFormField: function (blockInfo, field, idx) {
    const widgets = getWidgets()
    const value = blockInfo.data[field.name]
    let placeholder = field['default']
    const Widget = widgets.getWidgetComponentWithFallback(field.type)
    if (Widget.deserializeValue && placeholder != null) {
      placeholder = Widget.deserializeValue(placeholder, field.type)
    }

    const onChange = !this.props.onChange ? null : (value) => {
      blockInfo.data[field.name] = value
      this.props.onChange(this.props.value)
    }

    return (
      <widgets.FieldBox
        key={idx}
        value={value}
        placeholder={placeholder}
        field={field}
        onChange={onChange}
      />
    )
  },

  renderBlocks () {
    const widgets = getWidgets()

    return this.props.value.map((blockInfo, idx) => {
      // bad block is no block
      if (blockInfo === null) {
        return null
      }

      const fields = widgets.renderFieldRows(
        blockInfo.flowBlockModel.fields,
        null,
        this.renderFormField.bind(this, blockInfo)
      )

      return (
        <div key={blockInfo.localId} className='flow-block'>
          <div className='btn-group action-bar'>
            <button
              className='btn btn-default btn-xs'
              title={i18n.trans('UP')}
              disabled={idx === 0}
              onClick={this.moveBlock.bind(this, idx, -1)}>
              <i className='fa fa-fw fa-chevron-up' />
            </button>
            <button
              className='btn btn-default btn-xs'
              title={i18n.trans('DOWN')}
              disabled={idx >= this.props.value.length - 1}
              onClick={this.moveBlock.bind(this, idx, 1)}>
              <i className='fa fa-fw fa-chevron-down' />
            </button>
            <button
              className='btn btn-default btn-xs'
              title={i18n.trans('REMOVE')}
              onClick={this.removeBlock.bind(this, idx)}>
              <i className='fa fa-fw fa-times' />
            </button>
          </div>
          <h4 className='block-name'>{userLabel.format(blockInfo.flowBlockModel.name_i18n)}</h4>
          {fields}
        </div>
      )
    })
  },

  renderAddBlockSection () {
    let choices = []

    this.props.type.flowblock_order.forEach((key) => {
      let flowBlockModel = this.props.type.flowblocks[key]
      let label = flowBlockModel.button_label
        ? userLabel.format(flowBlockModel.button_label)
        : userLabel.format(flowBlockModel.name_i18n)
      choices.push([flowBlockModel.id, label, i18n.trans(flowBlockModel.name_i18n)])
    })

    const buttons = choices.map((item) => {
      const [key, label, title] = item
      return (
        <button
          className='btn btn-default'
          onClick={this.addNewBlock.bind(this, key)}
          title={title}
          key={key}>{label}</button>
      )
    })

    return (
      <div className='add-block'>
        <label>{i18n.trans('ADD_FLOWBLOCK') + ': '}</label>
        <div className='btn-group'>
          {buttons}
        </div>
      </div>
    )
  },

  render () {
    let {className} = this.props
    className = (className || '') + ' flow'

    return (
      <div className={className}>
        {this.renderBlocks()}
        {this.renderAddBlockSection()}
      </div>
    )
  }
})

export default {
  FlowWidget: FlowWidget
}
