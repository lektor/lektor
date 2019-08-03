'use strict'

/* eslint-env browser */

import React from 'react'
import createReactClass from 'create-react-class'
import i18n from '../i18n'
import flowformat from '../flowformat'
import { BasicWidgetMixin } from './mixins'
import userLabel from '../userLabel'
import widgets from '../widgets'

/* circular references require us to do this */
const getWidgets = () => {
  return widgets
}

// ever growing counter of block ids.  Good enough for what we do I think.
let lastBlockId = 0

const FlowWidget = createReactClass({
  displayName: 'FlowWidget',
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: (value, type) => {
      return flowformat.parseFlowFormat(value).map((item) => {
        const [id, lines] = item
        const flowBlock = type.flowblocks[id]
        if (flowBlock !== undefined) {
          return flowformat.deserializeFlowBlock(flowBlock, lines, ++lastBlockId)
        }
        return null
      })
    },

    serializeValue: (value) => {
      return flowformat.serializeFlowFormat(value.map((item) => {
        return [
          item.flowBlockModel.id,
          flowformat.serializeFlowBlock(item.flowBlockModel, item.data)
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
    this.props.value.push(flowformat.deserializeFlowBlock(flowBlockModel, [],
      ++lastBlockId))
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  },

  collapseBlock: function (idx) {
    this.props.value[idx].collapsed = true
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  },

  expandBlock: function (idx) {
    this.props.value[idx].collapsed = false
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
              title={this.props.value[idx].collapsed ? i18n.trans('Expand') : i18n.trans('Collapse')}
              onClick={this.props.value[idx].collapsed
                       ? this.expandBlock.bind(this, idx) : this.collapseBlock.bind(this, idx)}>
              <i className={this.props.value[idx].collapsed ? 'fa fa-expand' : 'fa fa-compress'} />
            </button>
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
          {this.props.value[idx].collapsed ? null : fields}
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
    let { className } = this.props
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
