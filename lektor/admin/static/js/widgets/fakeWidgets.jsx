'use strict';

import React from 'react'
import {BasicWidgetMixin, ValidationFailure} from './mixins'
import utils from '../utils'
import i18n from '../i18n'


const FakeWidgetMixin = {
  mixins: [BasicWidgetMixin],
  propTypes: {
    field: React.PropTypes.any,
  },

  statics: {
    isFakeWidget: true
  }
};


const LineWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render: function() {
    return <hr />;
  }
});

const SpacingWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render: function() {
    return <div className="spacing"></div>;
  }
});

const InfoWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render: function() {
    const label = i18n.trans(this.props.field.label_i18n)
    return (
      <div className="info">
        <p>
          {label ? <strong>{label + ': '}</strong> : null}
          {i18n.trans(this.props.field.description_i18n)}
        </p>
      </div>
    );
  }
});

const HeadingWidget = React.createClass({
  mixins: [FakeWidgetMixin],

  render: function() {
    return (
      <h3>{i18n.trans(this.props.type.heading_i18n)}</h3>
    )
  }
});


export default {
  LineWidget: LineWidget,
  SpacingWidget: SpacingWidget,
  InfoWidget: InfoWidget,
  HeadingWidget: HeadingWidget,
}
