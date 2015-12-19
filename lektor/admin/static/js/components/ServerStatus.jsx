'use strict';

var React = require('react');
var Router = require("react-router");

var Component = require('../components/Component');
var utils = require('../utils');
var i18n = require('../i18n');


class ServerStatus extends Component {

  constructor(props) {
    super(props);
    this.state = {
      serverIsUp: true,
      projectId: null
    };

    this.intervalId = null;
    this.onInterval = this.onInterval.bind(this);
  }

  componentDidMount() {
    super.componentDidMount();
    this.intervalId = window.setInterval(this.onInterval, 2000);
  }

  componentWillUnmount() {
    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
    super.componentWillUnmount();
  }

  onInterval() {
    utils.loadData('/ping')
      .then((resp) => {
        if (this.state.projectId === null) {
          this.setState({
            projectId: resp.project_id
          });
        }
        this.setState({
          serverIsUp: this.state.projectId === resp.project_id
        });
      }, () => {
        this.setState({
          serverIsUp: false
        });
      });
  }

  render() {
    if (this.state.serverIsUp) {
      return null;
    }
    return (
      <div className="server-down-panel">
        <div className="server-down-dialog">
          <h3>{i18n.trans('ERROR_SERVER_UNAVAILABLE')}</h3>
          <p>{i18n.trans('ERROR_SERVER_UNAVAILABLE_MESSAGE')}</p>
        </div>
      </div>
    );
  }
}

module.exports = ServerStatus;
