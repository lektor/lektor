'use strict'

import React from 'react'
import utils from '../utils'
import i18n from '../i18n'
import {BasicWidgetMixin} from './mixins'


var CheckboxesInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  statics: {
    deserializeValue: function(value) {
      if (value === '') {
        return null;
      }
      var rv = value.split(',').map(function(x) {
        return x.match(/^\s*(.*?)\s*$/)[1];
      });
      if (rv.length === 1 && rv[0] === '') {
        rv = [];
      }
      return rv;
    },

    serializeValue: function(value) {
      return (value || '').join(', ');
    }
  },

  onChange: function(field, event) {
    var newValue = utils.flipSetValue(this.props.value,
                                      field, event.target.checked);
    if (this.props.onChange) {
      this.props.onChange(newValue)
    }
  },

  isActive: function(field) {
    var value = this.props.value;
    if (value == null) {
      value = this.props.placeholder;
      if (value == null) {
        return false;
      }
    }
    for (var i = 0; i < value.length; i++) {
      if (value[i] === field) {
        return true;
      }
    }
    return false;
  },

  render: function() {
    var {className, value, placeholder, type, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    var choices = this.props.type.choices.map(function(item) {
      return (
        <div className={className} key={item[0]}>
          <label>
            <input type="checkbox"
              {...otherProps}
              checked={this.isActive(item[0])}
              onChange={this.onChange.bind(this, item[0])} />
            {i18n.trans(item[1])}
          </label>
        </div>
      );
    }.bind(this));
    return (
      <div className="checkboxes">
        {choices}
      </div>
    )
  }
});

var SelectInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.props.onChange(event.target.value);
  },

  render: function() {
    var {className, type, value, placeholder, onChange, ...otherProps} = this.props;
    value = value || placeholder;

    var choices = this.props.type.choices.map((item) => {
      return (
        <option key={item[0]} value={item[0]}>
          {i18n.trans(item[1])}
        </option>
      );
    });
    choices.unshift(
      <option key="" value="">{'----'}</option>
    );

    return (
      <div className="form-group">
        <div className={className}>
          <select
            className={this.getInputClass()}
            onChange={onChange ? this.onChange : null}
            value={value}
            {...otherProps}>
            {choices}
          </select>
        </div>
      </div>
    )
  }
});


export default {
  CheckboxesInputWidget: CheckboxesInputWidget,
  SelectInputWidget: SelectInputWidget,
}
