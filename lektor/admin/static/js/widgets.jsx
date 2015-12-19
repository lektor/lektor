'use strict';

var React = require('react');

var primitiveWidgets = require('./widgets/primitiveWidgets');
var multiWidgets = require('./widgets/multiWidgets');
var flowWidget = require('./widgets/flowWidget');
var fakeWidgets = require('./widgets/fakeWidgets');
var {BasicWidgetMixin} = require('./widgets/mixins');
var Component = require('./components/Component');
var ToggleGroup = require('./components/ToggleGroup');
var i18n = require('./i18n');


var widgetComponents = {
  'string': primitiveWidgets.SingleLineTextInputWidget,
  'strings': primitiveWidgets.MultiLineTextInputWidget,
  'date': primitiveWidgets.DateInputWidget,
  'integer': primitiveWidgets.IntegerInputWidget,
  'float': primitiveWidgets.FloatInputWidget,
  'boolean': primitiveWidgets.BooleanInputWidget,
  'url': primitiveWidgets.UrlInputWidget,
  'slug': primitiveWidgets.SlugInputWidget,
  'text': primitiveWidgets.MultiLineTextInputWidget,
  'html': primitiveWidgets.MultiLineTextInputWidget,
  'markdown': primitiveWidgets.MultiLineTextInputWidget,
  'flow': flowWidget.FlowWidget,
  'sortkey': primitiveWidgets.IntegerInputWidget,
  'checkboxes': multiWidgets.CheckboxesInputWidget,
  'select': multiWidgets.SelectInputWidget,
  'line': fakeWidgets.LineWidget,
  'spacing': fakeWidgets.SpacingWidget,
  'info': fakeWidgets.InfoWidget,
  'heading': fakeWidgets.HeadingWidget,
}


var FallbackWidget = React.createClass({
  mixins: [BasicWidgetMixin],
  render: function() {
    return (
      <div>
        <em>Widget for "{this.props.type.name}" not implemented</em>
      </div>
    )
  }
});


class FieldBox extends Component {

  render() {
    var {field, value, onChange, placeholder} = this.props;
    var className = 'col-md-' + getFieldColumns(field) + ' field-box';
    var innerClassName = 'field';
    var inner;

    if (field.name.substr(0, 1) == '_') {
      innerClassName += ' system-field';
    }

    var Widget = getWidgetComponentWithFallback(field.type);
    if (Widget.isFakeWidget) {
      inner = <Widget key={field.name} type={field.type} field={field} />;
    } else {
      var description = null;
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
  return widgetComponents[type.name] || null;
}

function getWidgetComponentWithFallback(type) {
  return widgetComponents[type.name] || FallbackWidget;
}

function getFieldColumns(field) {
  var widthSpec = (field.type.width || '1/1').split('/');
  return Math.min(12, Math.max(2, parseInt(
    12 * +widthSpec[0] / +widthSpec[1])));
}

function getFieldRows(fields, isIllegalField) {
  var normalFields = [];
  var systemFields = [];

  if (!isIllegalField) {
    isIllegalField = (x) => { return false; };
  }

  fields.forEach((field) => {
    if (!isIllegalField(field)) {
      if (field.name.substr(0, 1) == '_') {
        systemFields.push(field);
      } else {
        normalFields.push(field);
      }
    }
  });

  var processFields = (rv, rowType, fields) => {
    var currentColumns = 0;
    var row = [];

    fields.forEach((field) => {
      var columns = getFieldColumns(field);
      if (columns + currentColumns > 12) {
        rv.push([rowType, row]);
        currentColumns = 0;
        row = [];
      }
      row.push(field);
      currentColumns += columns;
    });

    if (row.length > 0) {
      rv.push([rowType, row]);
    }
  }

  var rv = [];
  processFields(rv, 'normal', normalFields);
  processFields(rv, 'system', systemFields);
  return rv;
}

function renderFieldRows(fields, isIllegalField, renderFunc) {
  var rv = {
    normal: [],
    system: [],
  };

  var rows = getFieldRows(fields, isIllegalField);

  rows.forEach((item, idx) => {
    var [rowType, row] = item;
    rv[rowType].push(
      <div className="row field-row" key={rowType + '-' + idx}>
        {row.map(renderFunc)}
      </div>
    );
  });

  return [
    rv.normal,
    rv.system.length > 1 ?
      <ToggleGroup
        key='sys'
        groupTitle={i18n.trans('SYSTEM_FIELDS')}
        defaultVisibility={false}>{rv.system}</ToggleGroup> : null
  ];
}


module.exports = {
  getWidgetComponent: getWidgetComponent,
  getWidgetComponentWithFallback: getWidgetComponentWithFallback,
  getFieldRows: getFieldRows,
  renderFieldRows: renderFieldRows,
  getFieldColumns: getFieldColumns,
  FallbackWidget: FallbackWidget,
  FieldBox: FieldBox,
};
