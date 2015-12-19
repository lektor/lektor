'use strict';

var React = require('react');
var ReactRouter = require('react-router');
var Component = require('./Component');


class Link extends Component {

  render() {
    var path = this.props.to;
    if (path.substr(0, 1) !== '/') {
      path = $LEKTOR_CONFIG.admin_root + '/' + path;
    }
    return (
      <ReactRouter.Link to={path} activeClassName="active">
        {this.props.children}
      </ReactRouter.Link>
    );
  }
}

Link.propTypes = {
  to: React.PropTypes.string
}


module.exports = Link;
