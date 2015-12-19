'use strict';

var React = require('react');
var Component = require('../components/Component');


class Dash extends Component {

  componentDidMount() {
    super.componentDidMount();
    var rootPreview = $LEKTOR_CONFIG.admin_root + '/root/preview';
    this.props.history.pushState(null, rootPreview);
  }

  render() {
    return null;
  }
}

module.exports = Dash;
