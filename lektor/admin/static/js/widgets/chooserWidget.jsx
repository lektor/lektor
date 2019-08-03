'use strict'

/* eslint-env browser */

import PropTypes from 'prop-types'
import React from 'react'
import i18n from '../i18n'
import flowformat from '../flowformat'
import widgets from '../widgets'

/* circular references require us to do this */
const getWidgets = () => {
  return widgets
}

class ChooserWidget extends React.Component {
  // XXX: the modification of props is questionable

  moveBlock (idx, offset, event) {
    event.preventDefault()

    const newIndex = idx + offset
    if (newIndex < 0 || newIndex >= this.props.value.blocks.length) {
      return
    }

    const tmp = this.props.value.blocks[newIndex]
    this.props.value.blocks[newIndex] = this.props.value.blocks[idx]
    this.props.value.blocks[idx] = tmp

    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  }

  removeBlock (idx, event) {
    event.preventDefault()

    if (confirm(i18n.trans('REMOVE_FLOWBLOCK_PROMPT'))) {
      this.props.value.blocks.splice(idx, 1)
      if (this.props.onChange) {
        this.props.onChange(this.props.value)
      }

      if (this.props.value.blocks.length === 0) {
        this.props.value.displayId = false
      } else {
        const newVal = this.props.value.blocks[idx] ? this.props.value.blocks[idx] : this.props.value.blocks[idx - 1]
        this.props.value.displayId = newVal.localId
      }
      if (this.props.onChange) {
        this.props.onChange(this.props.value)
      }
    }
  }

  addNewBlock (event) {
    if (event) event.preventDefault()

    // just use the first flowblock type, as they're all the same
    const key = this.props.type.flowblock_order[0]
    const flowBlockModel = this.props.type.flowblocks[key]

    // find the first available id for this new block - use findMax + 1
    const blockIds = this.props.value.blocks.map(block => block.localId)
    const newBlockId = blockIds.length === 0 ? 1 : Math.max(...blockIds) + 1

    // this is a rather ugly way to do this, but hey, it works.
    this.props.value.blocks.push(flowformat.deserializeFlowBlock(flowBlockModel, [], newBlockId))
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
    this.props.value.displayId = newBlockId
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
  }

  renderBlocks () {
    const widgets = getWidgets()
    const idx = this.getCurrentBlockIndex()
    if (idx === false) return null

    // just use the first flowblock fields, as there's only one flowblock type
    const blockInfo = this.props.value.blocks[idx]
    const rows = widgets.getFieldRows(this.props.value.blocks[0].flowBlockModel.fields, null)

    const renderedRows = rows.map((item, idx) => {
      const [rowType, row] = item

      const fields = row.map((field, idx) => {
        const onChange = !this.props.onChange ? null : (value) => {
          blockInfo.data[field.name] = value
          this.props.onChange(this.props.value)
        }
        const value = blockInfo.data[field.name]
        const placeholder = ''

        return (
          <widgets.FieldBox
            key={idx}
            value={value}
            placeholder={placeholder}
            field={field}
            onChange={onChange}
          />
        )
      })

      return (
        <div className='row field-row' key={rowType + '-' + idx}>
          {fields}
        </div>
      )
    })

    return renderedRows
  }

  getCurrentBlockIndex () {
    if (this.props.value.displayId === false) return false
    return this.props.value.blocks.findIndex(el => el.localId === this.props.value.displayId)
  }

  keyFieldValue () {
    const idx = this.getCurrentBlockIndex()
    if (idx === false) return false
    return this.props.value.blocks[idx].data[this.props.type.key_field]
  }

  keyFieldIsDuplicate () {
    const keyFields = this.props.value.blocks.reduce((res, val) => {
      if (val.localId === this.props.value.displayId) return res
      return res.concat(val.data[this.props.type.key_field])
    }, [])

    const currentVal = this.keyFieldValue()
    if (currentVal === false) return false
    return keyFields.indexOf(currentVal) !== -1
  }

  renderChooserButtons () {
    const idx = this.getCurrentBlockIndex()
    return (
      <div className='btn-group action-bar'>
        <button
          className='btn btn-default btn-xs'
          title={i18n.trans('UP')}
          disabled={idx === false || idx === 0}
          onClick={this.moveBlock.bind(this, idx, -1)}>
          <i className='fa fa-fw fa-chevron-up' />
        </button>
        <button
          className='btn btn-default btn-xs'
          title={i18n.trans('DOWN')}
          disabled={idx === false || idx >= this.props.value.blocks.length - 1}
          onClick={this.moveBlock.bind(this, idx, 1)}>
          <i className='fa fa-fw fa-chevron-down' />
        </button>
        <button
          className='btn btn-default btn-xs'
          title={i18n.trans('REMOVE')}
          disabled={idx === false}
          onClick={this.removeBlock.bind(this, idx)}>
          <i className='fa fa-fw fa-times' />
        </button>
        <button
          className='btn btn-default btn-xs'
          title={i18n.trans('ADD_FLOWBLOCK')}
          disabled={this.keyFieldValue() && (this.keyFieldValue().trim() === '' || this.keyFieldIsDuplicate())}
          onClick={this.addNewBlock.bind(this)}>
          <i className='fa fa-fw fa-plus' />
        </button>
      </div>
    )
  }

  render () {
    let { className } = this.props
    className = (className || '') + ' flow'

    const selectOptions = this.props.value.blocks.map((val, idx) => {
      return <option key={val.localId} value={val.localId}>{val.data[this.props.type.key_field]}</option>
    })

    // check for key field error
    let help = null
    const keyFieldVal = this.keyFieldValue()
    if (keyFieldVal && keyFieldVal.trim() === '') {
      className += ' has-feedback has-error'
      help = <div className='validation-block validation-block-error'>Key Field can't be empty</div>
    } else if (this.keyFieldIsDuplicate()) {
      className += ' has-feedback has-error'
      help = <div className='validation-block validation-block-error'>Key Field must be unique</div>
    }

    const selectChange = event => {
      this.props.value.displayId = parseInt(event.target.value)
      if (this.props.onChange) {
        this.props.onChange(this.props.value)
      }
    }

    return (
      <div className={className}>
        <div className='flow-block row equal'>
          <div className='col-md-2 form-group chooser-select'>
            {help}
            <select
              size='2'
              className='form-control'
              onChange={selectChange}
              value={this.props.value.displayId}>
              {selectOptions}
            </select>
            {this.renderChooserButtons()}
          </div>
          <div className='col-md-10'>
            {this.renderBlocks()}
          </div>
        </div>
      </div>
    )
  }
}

ChooserWidget.deserializeValue = (value, type) => {
  let blockId = 0
  const blocks = flowformat.parseFlowFormat(value).map((item) => {
    const [id, lines] = item
    const flowBlock = type.flowblocks[id]
    if (flowBlock !== undefined) {
      return flowformat.deserializeFlowBlock(flowBlock, lines, ++blockId)
    }
    return null
  })
  return {
    blocks: blocks,
    displayId: blocks.length === 0 ? false : 1
  }
}

ChooserWidget.serializeValue = (value) => {
  const blocks = value.blocks
  return flowformat.serializeFlowFormat(blocks.map((item) => {
    return [
      item.flowBlockModel.id,
      flowformat.serializeFlowBlock(item.flowBlockModel, item.data)
    ]
  }))
}

ChooserWidget.propTypes = {
  value: PropTypes.any,
  type: PropTypes.object,
  placeholder: PropTypes.any,
  onChange: PropTypes.func
}

export default {
  ChooserWidget: ChooserWidget
}
