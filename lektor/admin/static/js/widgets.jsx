'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import { DateInputWidget, IntegerInputWidget, FloatInputWidget, UrlInputWidget, SlugInputWidget, BooleanInputWidget, MultiLineTextInputWidget, SingleLineTextInputWidget } from './widgets/primitiveWidgets'
import { CheckboxesInputWidget, SelectInputWidget } from './widgets/multiWidgets'
import { FlowWidget } from './widgets/flowWidget'
import { LineWidget, SpacingWidget, InfoWidget, HeadingWidget } from './widgets/fakeWidgets'
import { widgetPropTypes } from './widgets/mixins'
import ToggleGroup from './components/ToggleGroup'
import i18n from './i18n'

const widgetComponents = {
  'singleline-text': SingleLineTextInputWidget,
  'multiline-text': MultiLineTextInputWidget,
  datepicker: DateInputWidget,
  integer: IntegerInputWidget,
  float: FloatInputWidget,
  checkbox: BooleanInputWidget,
  url: UrlInputWidget,
  slug: SlugInputWidget,
  flow: FlowWidget,
  checkboxes: CheckboxesInputWidget,
  select: SelectInputWidget,
  'f-line': LineWidget,
  'f-spacing': SpacingWidget,
  'f-info': InfoWidget,
  'f-heading': HeadingWidget
}

function FallbackWidget (props) {
  return (
    <div>
      <em>
        Widget "{props.type.widget}" not implemented
        (used by type "{props.type.name}")
      </em>
    </div>
  )
}
FallbackWidget.propTypes = widgetPropTypes

class FieldBox extends React.PureComponent {
  render () {
    const { field, value, placeholder, disabled } = this.props
    const onChange = this.props.onChange ? this.props.onChange : (value) => this.props.setFieldValue(field, value)
    const className = 'col-md-' + getFieldColumns(field) + ' field-box'
    let innerClassName = 'field'
    let inner

    if (field.name.substr(0, 1) === '_') {
      innerClassName += ' system-field'
    }

    const Widget = getWidgetComponentWithFallback(field.type)
    if (Widget.isFakeWidget) {
      inner = <Widget key={field.name} type={field.type} field={field} />
    } else {
      let description = null
      if (field.description_i18n) {
        description = (
          <div className='help-text'>
            {i18n.trans(field.description_i18n)}
          </div>
        )
      }
      inner = (
        <dl className={innerClassName}>
          {!field.hide_label ? <dt>{i18n.trans(field.label_i18n)}</dt> : null}
          <dd>{description}
            <Widget
              value={value}
              onChange={onChange}
              type={field.type}
              placeholder={placeholder}
              disabled={disabled}
            />
          </dd>
        </dl>
      )
    }

    return (
      <div className={className} key={field.name}>
        {inner}
      </div>
    )
  }
}

FieldBox.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
  field: PropTypes.any,
  placeholder: PropTypes.any
}

const getWidgetComponent = (type) => {
  return widgetComponents[type.widget] || null
}

const getWidgetComponentWithFallback = (type) => {
  return widgetComponents[type.widget] || FallbackWidget
}

const getFieldColumns = (field) => {
  const widthSpec = (field.type.width || '1/1').split('/')
  return Math.min(12, Math.max(2, parseInt(
    12 * +widthSpec[0] / +widthSpec[1])))
}

const getFieldRows = (fields, isIllegalField) => {
  const normalFields = []
  const systemFields = []

  if (!isIllegalField) {
    isIllegalField = (x) => { return false }
  }

  fields.forEach((field) => {
    if (!isIllegalField(field)) {
      if (field.name.substr(0, 1) === '_') {
        systemFields.push(field)
      } else {
        normalFields.push(field)
      }
    }
  })

  const processFields = (rv, rowType, fields) => {
    let currentColumns = 0
    let row = []

    fields.forEach((field) => {
      const columns = getFieldColumns(field)
      if (columns + currentColumns > 12) {
        rv.push([rowType, row])
        currentColumns = 0
        row = []
      }
      row.push(field)
      currentColumns += columns
    })

    if (row.length > 0) {
      rv.push([rowType, row])
    }
  }

  const rv = []
  processFields(rv, 'normal', normalFields)
  processFields(rv, 'system', systemFields)
  return rv
}

const renderFieldRows = (fields, isIllegalField, renderFunc) => {
  const rv = {
    normal: [],
    system: []
  }

  const rows = getFieldRows(fields, isIllegalField)

  rows.forEach((item, idx) => {
    const [rowType, row] = item
    rv[rowType].push(
      <div className='row field-row' key={rowType + '-' + idx}>
        {row.map(renderFunc)}
      </div>
    )
  })

  return [
    rv.normal,
    rv.system.length > 1
      ? (
        <ToggleGroup
          key='sys'
          groupTitle={i18n.trans('SYSTEM_FIELDS')}
          defaultVisibility={false}
        >
          {rv.system}
        </ToggleGroup>
      ) : null
  ]
}

export default {
  getWidgetComponent: getWidgetComponent,
  getWidgetComponentWithFallback: getWidgetComponentWithFallback,
  getFieldRows: getFieldRows,
  renderFieldRows: renderFieldRows,
  getFieldColumns: getFieldColumns,
  FieldBox: FieldBox
}
