'use strict'

/* eslint-env browser */

import PropTypes from 'prop-types'
import React from 'react'
import i18n from '../i18n'
import metaformat from '../metaformat'
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

class ChooserWidget extends React.Component {
  constructor (props) {
    super(props)

    this.state = {
      displayId: this.props.value.length === 0 ? false : 1
    }
  }

  // XXX: the modification of props is questionable

  moveBlock (idx, offset, event) {
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
  }

  removeBlock (idx, event) {
    event.preventDefault()

    if (confirm(i18n.trans('REMOVE_FLOWBLOCK_PROMPT'))) {
      this.props.value.splice(idx, 1)
      if (this.props.onChange) {
        this.props.onChange(this.props.value)
      }

      if (this.props.value.length === 0) {
        this.setState({
          displayId: false
        })
      } else {
        const newVal = this.props.value[idx] ? this.props.value[idx] : this.props.value[idx - 1]
        this.setState({
          displayId: newVal.localId
        })
      }
    }
  }

  addNewBlock (event) {
    if (event) event.preventDefault()

    // just use the first flowblock type, as they're all the same
    const idx = Object.keys(this.props.type.flowblocks)[0]
    const key = this.props.type.flowblocks[idx].id

    const flowBlockModel = this.props.type.flowblocks[key]

    // find the first available id for this new block - use findMax + 1
    const blockIds = this.props.value.map(block => block.localId)
    const newBlockId = blockIds.length === 0 ? 1 : Math.max(...blockIds) + 1

    // this is a rather ugly way to do this, but hey, it works.
    this.props.value.push(deserializeFlowBlock(flowBlockModel, [], newBlockId))
    if (this.props.onChange) {
      this.props.onChange(this.props.value)
    }
    this.setState({
      displayId: newBlockId
    })
  }

  renderBlocks () {
    const widgets = getWidgets()
    const idx = this.getCurrentBlockIndex()
    if (idx === false) return null

    // just use the first flowblock fields, as there's only one flowblock type
    const blockInfo = this.props.value[idx]
    const rows = widgets.getFieldRows(this.props.value[0].flowBlockModel.fields, null)

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
    if (this.state.displayId === false) return false
    return this.props.value.findIndex(el => el.localId === this.state.displayId)
  }

  keyFieldValue () {
    const idx = this.getCurrentBlockIndex()
    if (idx === false) return false
    return this.props.value[idx].data[this.props.type.key_field]
  }

  keyFieldIsDuplicate () {
    const keyFields = this.props.value.reduce((res, val) => {
      if (val.localId === this.state.displayId) return res
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
          disabled={idx === false || idx >= this.props.value.length - 1}
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

    const selectOptions = this.props.value.map((val, idx) => {
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
      this.setState({
        displayId: parseInt(event.target.value)
      })
    }

    return (
      <div className={className}>
        <div className='flow-block row equal'>
          <div className='col-md-3 form-group chooser-select'>
            {help}
            <select
              size='2'
              className='form-control'
              onChange={selectChange}
              value={this.state.displayId}>
              {selectOptions}
            </select>
            {this.renderChooserButtons()}
          </div>
          <div className='col-md-9'>
            {this.renderBlocks()}
          </div>
        </div>
      </div>
    )
  }
}

ChooserWidget.deserializeValue = (value, type) => {
  let blockId = 0
  return parseFlowFormat(value).map((item) => {
    const [id, lines] = item
    const flowBlock = type.flowblocks[id]
    if (flowBlock !== undefined) {
      return deserializeFlowBlock(flowBlock, lines, ++blockId)
    }
    return null
  })
}

ChooserWidget.serializeValue = (value) => {
  return serializeFlowFormat(value.map((item) => {
    return [
      item.flowBlockModel.id,
      serializeFlowBlock(item.flowBlockModel, item.data)
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
