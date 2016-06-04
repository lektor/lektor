'use strict';

var React = require('react');
var {BasicWidgetMixin, ValidationFailure} = require('./mixins');
var utils = require('../utils');
var userLabel = require('../userLabel');
var i18n = require('../i18n');
var moment = require('moment-timezone');
var momentLocalizer = require('react-widgets/lib/localizers/moment');
var DateTimePicker = require('react-widgets/lib/DateTimePicker');

moment.locale(i18n.currentLanguage);
momentLocalizer(moment);
var guessedUserTZ = moment.tz.guess();

function isTrue(value) {
  return value == 'true' || value == 'yes' || value == '1';
}

var InputWidgetMixin = {
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    var value = event.target.value;
    if (this.postprocessValue) {
      value = this.postprocessValue(value);
    }
    this.props.onChange(value);
  },

  render: function() {
    var {type, onChange, className, ...otherProps} = this.props;
    var help = null;
    var failure = this.getValidationFailure();
    var className = (className || '');
    className += ' input-group';

    if (failure !== null) {
      className += ' has-feedback has-' + failure.type;
      var valClassName = 'validation-block validation-block-' + failure.type;
      help = <div className={valClassName}>{failure.message}</div>;
    }

    var addon = null;
    var configuredAddon = type.addon_label_i18n;
    if (configuredAddon) {
      addon = userLabel.format(configuredAddon);
    } else if (this.getInputAddon) {
      addon = this.getInputAddon();
    }

    return (
      <div className="form-group">
        <div className={className}>
          <input
            type={this.getInputType()}
            className={this.getInputClass()}
            onChange={onChange ? this.onChange : undefined}
            {...otherProps} />
          {addon ? <span className="input-group-addon">{addon}</span> : null}
        </div>
        {help}
      </div>
    )
  }
};


var SingleLineTextInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <i className="fa fa-paragraph"></i>;
  }
});

var SlugInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue: function(value) {
    return value.replace(/\s+/g, '-');
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <i className="fa fa-link"></i>;
  }
});

var IntegerInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue: function(value) {
    return value.match(/^\s*(.*?)\s*$/)[1];
  },

  getValidationFailureImpl: function() {
    if (this.props.value && !this.props.value.match(/^\d+$/)) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_NUMBER')
      });
    }
    return null;
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return '0';
  }
});

var FloatInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  postprocessValue: function(value) {
    return value.match(/^\s*(.*?)\s*$/)[1];
  },

  getValidationFailureImpl: function() {
    if (this.props.value && parseFloat(this.props.value) == NaN) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_NUMBER')
      });
    }
    return null;
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return '0.0';
  }
});

var DateInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  parseDate: function(inputDateStr) {
    var inputDate = moment(inputDateStr, moment.ISO_8601, true);
    if(inputDate.isValid()) {
      return new Date(inputDate.toISOString());
    }
  },

  onChange: function(inputDate) {
    if(this.props.onChange) {
      if(inputDate) {
        this.props.onChange(inputDate.getFullYear() + "-" +
                            ("0" + (inputDate.getMonth() + 1)).slice(-2) + "-" +
                            ("0" + inputDate.getDate()).slice(-2));
      } else {
        this.props.onChange("");
      }
    }
  },

  render: function() {
    var {className, type, value, placeholder, onChange, ...otherProps} = this.props;

    var className = (className || '')
    var inputDate;
    if(value) {
      inputDate = this.parseDate(value);
    }

    return (
          <div className="form-group">
            <div className={className}>
                <DateTimePicker
                  className={this.getInputClass()}
                  format={"MMM DD YYYY"}
                  editFormat={"YYYY-MM-DD"}
                  parse={this.parseDate}
                  time={false}
                  onChange={onChange ? this.onChange : undefined}
                  value={inputDate ? inputDate : null}
                  {...otherProps} />
            </div>
          </div>
    )
  }
});


var DateTimeInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  parseDateTime: function(inputDateTimeStr) {
    var dt;
    var chunks = inputDateTimeStr.split(' ');
    if (chunks.length > 1 && chunks.length <= 3) {
      if(chunks.length == 2) {
        dt = moment.tz(chunks.slice(0,2).join(' '), guessedUserTZ);
      } else {
        // TODO if the timezone is invalid momentjs ignores it and moment.isValid still returns true
        // needs a check for valid timezones
        dt = moment.tz(chunks.slice(0,2).join(' '), chunks[2]);
      }
      if (dt.isValid()) {
        return dt;
      }
    }
  },

  //2016-01-13 01:02:03 America/Dominica
  getFormattedDateTime: function() {
    var rv = this.datetime.getFullYear() + "-" +
             ("0" + (this.datetime.getMonth() + 1)).slice(-2) + "-" +
             ("0" + this.datetime.getDate()).slice(-2) + " " +
             ("0" + this.datetime.getHours()).slice(-2) + ":" +
             ("0" + this.datetime.getMinutes()).slice(-2) + ":" +
             ("0" + this.datetime.getSeconds()).slice(-2);
    if(this.tz) {
      rv += " " + this.tz;
    }
    return rv;
  },

  getValidationFailureImpl: function() {
    if (this.props.value && false) {
      return new ValidationFailure({
        //XXX: create timezone error message
        message: i18n.trans('ERROR_INVALID_DATETIME')
      });
    }
    return null;
  },

  onChange: function() {
    if(this.props.onChange) {
      if(this.datetime) {
        this.props.onChange(this.getFormattedDateTime());
      } else {
        this.props.onChange("");
      }
    }
  },

  onDTChange: function(inputDateTime) {
    this.datetime = inputDateTime? inputDateTime : undefined;
    this.onChange();
  },

  onTZChange: function(event) {
    var value = event.target.value;
    this.tz = value? value : "";
    this.onChange();
  },

  render: function() {
    var {className, type, value, placeholder, onChange, ...otherProps} = this.props;
    var inputDateTime;
    if(value) {
      inputDateTime = this.parseDateTime(value);
    }
    if(inputDateTime) {
      this.datetime = inputDateTime.toDate();
      this.tz = inputDateTime._z.name;
    } else {
      this.tz = guessedUserTZ;
    }
    var tzClassName = className;

    return (
          <div className="form-group">
            <div className={className}>
                <DateTimePicker
                  className={this.getInputClass()}
                  format={"MMM DD YYYY HH:mm"}
                  editFormat={"YYYY-MM-DD HH:mm"}
                  onChange={onChange ? this.onDTChange : undefined}
                  value={this.datetime ? this.datetime : null}
                  {...otherProps} />
              </div>
              <div className={tzClassName}>
                <input
                  className={this.getInputClass()}
                  type={'text'}
                  onChange={onChange ? this.onTZChange : undefined}
                  value={this.tz ? this.tz : guessedUserTZ}
                  />
                <span className="input-group-addon">
                  <i className="fa fa-globe"></i>
                </span>
            </div>
          </div>
    )
  }
});

var UrlInputWidget = React.createClass({
  mixins: [InputWidgetMixin],

  getValidationFailureImpl: function() {
    if (this.props.value && !utils.isValidUrl(this.props.value)) {
      return new ValidationFailure({
        message: i18n.trans('ERROR_INVALID_URL')
      });
    }
    return null;
  },

  getInputType: function() {
    return 'text';
  },

  getInputAddon: function() {
    return <i className="fa fa-external-link"></i>;
  }
});

var MultiLineTextInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.recalculateSize();
    if (this.props.onChange) {
      this.props.onChange(event.target.value);
    }
  },

  componentDidMount: function() {
    this.recalculateSize();
    window.addEventListener('resize', this.recalculateSize);
  },

  componentWillUnmount: function() {
    window.removeEventListener('resize', this.recalculateSize);
  },

  componentDidUpdate: function(prevProps) {
    this.recalculateSize();
  },

  isInAutoResizeMode: function() {
    return this.props.rows === undefined;
  },

  recalculateSize: function() {
    if (!this.isInAutoResizeMode()) {
      return;
    }
    var diff;
    var node = this.refs.ta;

    if (window.getComputedStyle) {
      var s = window.getComputedStyle(node);
      if (s.getPropertyValue('box-sizing') === 'border-box' ||
          s.getPropertyValue('-moz-box-sizing') === 'border-box' ||
          s.getPropertyValue('-webkit-box-sizing') === 'border-box') {
        diff = 0;
      } else {
        diff = (
          parseInt(s.getPropertyValue('padding-bottom') || 0, 10) +
          parseInt(s.getPropertyValue('padding-top') || 0, 10)
        );
      }
    } else {
      diff = 0;
    }

    var updateScrollPosition = jQuery(node).is(':focus');
    //Cross-browser compatibility for scroll position
    var oldScrollTop = document.documentElement.scrollTop || document.body.scrollTop;
    var oldHeight = jQuery(node).outerHeight();

    node.style.height = 'auto';
    var newHeight = (node.scrollHeight - diff);
    node.style.height = newHeight + 'px';

    if (updateScrollPosition) {
      window.scrollTo(
        document.body.scrollLeft, oldScrollTop + (newHeight - oldHeight));
    }
  },

  render: function() {
    var {className, type, onChange, style, ...otherProps} = this.props;
    var className = (className || '');

    style = style || {};
    if (this.isInAutoResizeMode()) {
      style.display = 'block';
      style.overflow = 'hidden';
      style.resize = 'none';
    }

    return (
      <div className={className}>
        <textarea
          ref="ta"
          className={this.getInputClass()}
          onChange={onChange ? this.onChange : undefined}
          style={style}
          {...otherProps} />
      </div>
    )
  }
});

var BooleanInputWidget = React.createClass({
  mixins: [BasicWidgetMixin],

  onChange: function(event) {
    this.props.onChange(event.target.checked ? 'yes' : 'no');
  },

  componentDidMount: function() {
    var checkbox = this.refs.checkbox;
    if (!this.props.value && this.props.placeholder) {
      checkbox.indeterminate = true;
      checkbox.checked = isTrue(this.props.placeholder);
    } else {
      checkbox.indeterminate = false;
    }
  },

  render: function() {
    var {className, type, placeholder, onChange, value, ...otherProps} = this.props;
    className = (className || '') + ' checkbox';

    return (
      <div className={className}>
        <label>
          <input type="checkbox"
            {...otherProps}
            ref='checkbox'
            checked={isTrue(value)}
            onChange={onChange ? this.onChange : undefined} />
          {type.checkbox_label_i18n ? i18n.trans(type.checkbox_label_i18n) : null}
        </label>
      </div>
    )
  }
});

module.exports = {
  SingleLineTextInputWidget: SingleLineTextInputWidget,
  SlugInputWidget: SlugInputWidget,
  IntegerInputWidget: IntegerInputWidget,
  FloatInputWidget: FloatInputWidget,
  DateInputWidget: DateInputWidget,
  DateTimeInputWidget: DateTimeInputWidget,
  UrlInputWidget: UrlInputWidget,
  MultiLineTextInputWidget: MultiLineTextInputWidget,
  BooleanInputWidget: BooleanInputWidget,
};
