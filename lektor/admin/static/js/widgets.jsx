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

export class FieldBox extends React.PureComponent {
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

export function getWidgetComponent (type) {
  return widgetComponents[type.widget] || null
}

export function getWidgetComponentWithFallback (type) {
  return widgetComponents[type.widget] || FallbackWidget
}

/**
 * Get the width of a field in columns.
 */
function getFieldColumns (field) {
  const widthSpec = (field.type.width || '1/1').split('/')
  return Math.min(12, Math.max(2, parseInt(
    12 * +widthSpec[0] / +widthSpec[1])))
}

/**
 * Process fields into rows.
 */
function processFields (fields) {
  const rows = []
  let currentColumns = 0
  let row = []

  fields.forEach((field) => {
    const columns = getFieldColumns(field)
    if (columns + currentColumns > 12) {
      rows.push(row)
      currentColumns = 0
      row = []
    }
    row.push(field)
    currentColumns += columns
  })

  if (row.length > 0) {
    rows.push(row)
  }
  return rows
}

/**
 * Split the fields into normal and system fields and process into rows.
 */
function getFieldRows (fields, isIllegalField) {
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

  return [processFields(normalFields), processFields(systemFields)]
}

/**
 * Render field rows, using a render function and ignoring 'illegal' fields.
 */
export function renderFieldRows (fields, isIllegalField, renderFunc) {
  const [normalRows, systemRows] = getFieldRows(fields, isIllegalField)

  const normalRowElements = normalRows.map((row, idx) => (
    <div className='row field-row' key={'normal-' + idx}>
      {row.map(renderFunc)}
    </div>
  ))
  const systemRowElements = systemRows.map((row, idx) => (
    <div className='row field-row' key={'system-' + idx}>
      {row.map(renderFunc)}
    </div>
  ))

  return [
    normalRowElements,
    systemRowElements.length > 1
      ? (
        <ToggleGroup
          key='sys'
          groupTitle={i18n.trans('SYSTEM_FIELDS')}
          defaultVisibility={false}
        >
          {systemRowElements}
        </ToggleGroup>
      ) : null
  ]
}
