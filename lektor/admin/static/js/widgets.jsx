'use strict'

import React from 'react'
import primitiveWidgets from './widgets/primitiveWidgets'
import multiWidgets from './widgets/multiWidgets'
import flowWidget from './widgets/flowWidget'
import fakeWidgets from './widgets/fakeWidgets'
import {BasicWidgetMixin} from './widgets/mixins'
import Component from './components/Component'
import ToggleGroup from './components/ToggleGroup'
import i18n from './i18n'


const widgetComponents = {
  'singleline-text': primitiveWidgets.SingleLineTextInputWidget,
  'multiline-text': primitiveWidgets.MultiLineTextInputWidget,
  'datepicker': primitiveWidgets.DateInputWidget,
  'integer': primitiveWidgets.IntegerInputWidget,
  'float': primitiveWidgets.FloatInputWidget,
  'checkbox': primitiveWidgets.BooleanInputWidget,
  'url': primitiveWidgets.UrlInputWidget,
  'slug': primitiveWidgets.SlugInputWidget,
  'flow': flowWidget.FlowWidget,
  'checkboxes': multiWidgets.CheckboxesInputWidget,
  'select': multiWidgets.SelectInputWidget,
  'f-line': fakeWidgets.LineWidget,
  'f-spacing': fakeWidgets.SpacingWidget,
  'f-info': fakeWidgets.InfoWidget,
  'f-heading': fakeWidgets.HeadingWidget,
}


const FallbackWidget = React.createClass({
  mixins: [BasicWidgetMixin],
  render: function() {
    return (
      <div>
        <em>
          Widget "{this.props.type.widget}" not implemented
          (used by type "{this.props.type.name}")
        </em>
      </div>
    )
  }
})


class FieldBox extends Component {

  render() {
    const {field, value, onChange, placeholder} = this.props
    const className = 'col-md-' + getFieldColumns(field) + ' field-box'
    let innerClassName = 'field';
    let inner;

    if (field.name.substr(0, 1) == '_') {
      innerClassName += ' system-field';
    }

    const Widget = getWidgetComponentWithFallback(field.type)
    if (Widget.isFakeWidget) {
      inner = <Widget key={field.name} type={field.type} field={field} />;
    } else {
      let description = null;
      if (field.description_i18n) {
        description = (
          <div className="help-text">
            {i18n.trans(field.description_i18n)}
          </div>
        );
      }
      inner = (
        <dl className={innerClassName}>
          {!field.hide_label ? <dt>{i18n.trans(field.label_i18n)}</dt> : null}
          <dd>{description}<Widget
            value={value}
            onChange={onChange}
            type={field.type}
            placeholder={placeholder}
          /></dd>
        </dl>
      );
    }

    return (
      <div className={className} key={field.name}>
        {inner}
      </div>
    );
  }
}

FieldBox.propTypes = {
  value: React.PropTypes.any,
  onChange: React.PropTypes.func,
  field: React.PropTypes.any,
  placeholder: React.PropTypes.any,
}


function getWidgetComponent(type) {
  return widgetComponents[type.widget] || null;
}

function getWidgetComponentWithFallback(type) {
  return widgetComponents[type.widget] || FallbackWidget;
}

function getFieldColumns(field) {
  const widthSpec = (field.type.width || '1/1').split('/')
  return Math.min(12, Math.max(2, parseInt(
    12 * +widthSpec[0] / +widthSpec[1])));
}

function getFieldRows(fields, isIllegalField) {
  const normalFields = []
  const systemFields = []

  if (!isIllegalField) {
    isIllegalField = (x) => { return false }
  }

  fields.forEach((field) => {
    if (!isIllegalField(field)) {
      if (field.name.substr(0, 1) == '_') {
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

function renderFieldRows(fields, isIllegalField, renderFunc) {
  const rv = {
    normal: [],
    system: []
  }

  const rows = getFieldRows(fields, isIllegalField)

  rows.forEach((item, idx) => {
    const [rowType, row] = item
    rv[rowType].push(
      <div className="row field-row" key={rowType + '-' + idx}>
        {row.map(renderFunc)}
      </div>
    )
  })

  return [
    rv.normal,
    rv.system.length > 1 ?
      <ToggleGroup
        key='sys'
        groupTitle={i18n.trans('SYSTEM_FIELDS')}
        defaultVisibility={false}>{rv.system}</ToggleGroup> : null
  ]
}

export default {
  getWidgetComponent: getWidgetComponent,
  getWidgetComponentWithFallback: getWidgetComponentWithFallback,
  getFieldRows: getFieldRows,
  renderFieldRows: renderFieldRows,
  getFieldColumns: getFieldColumns,
  FallbackWidget: FallbackWidget,
  FieldBox: FieldBox
}
