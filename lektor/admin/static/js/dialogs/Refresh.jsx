'use strict';

var React = require('react');
var Component = require('../components/Component');

var SlideDialog = require('../components/SlideDialog');
var utils = require('../utils');
var i18n = require('../i18n');
var dialogSystem = require('../dialogSystem');


class Refresh extends Component {

  constructor(props) {
    super(props);
    this.state = {
      currentState: 'IDLE'
    };
  }

  componentDidMount() {
    super.componentDidMount();
    this.syncDialog();
  }

  preventNavigation() {
    return !this.isSafeToNavigate();
  }

  isSafeToNavigate() {
    return this.state.currentState === 'IDLE' ||
      this.state.currentState === 'DONE';
  }

  onRefresh() {
    this.setState({
      currentState: 'CLEANING'
    });
    utils.apiRequest('/clean', {
      method: 'POST'
    }).then((resp) => {
      this.setState({
        currentState: 'DONE'
      })
    });
  }

  onCancel() {
    dialogSystem.dismissDialog();
  }

  render() {
    var progress = null;
    if (this.state.currentState !== 'IDLE') {
      progress = (
        <div>
          <h3>{this.state.currentState !== 'DONE'
            ? i18n.trans('CURRENTLY_REFRESHING_BUILD')
            : i18n.trans('REFRESHING_BUILD_DONE')}</h3>
        </div>
      );
    }

    return (
      <SlideDialog
        hasCloseButton={false}
        closeOnEscape={true}
        title={i18n.trans('REFRESH_BUILD')}>
        <p>{i18n.trans('REFRESH_BUILD_NOTE')}</p>
        {progress}
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            disabled={!this.isSafeToNavigate()}
            onClick={this.onRefresh.bind(this)}>{i18n.trans('REFRESH_BUILD')}</button>
          <button type="submit" className="btn btn-default"
            disabled={!this.isSafeToNavigate()}
            onClick={this.onCancel.bind(this)}>{i18n.trans(
              this.state.currentState === 'DONE' ? 'CLOSE' : 'CANCEL')}</button>
        </div>
      </SlideDialog>
    );
  }
}

module.exports = Refresh;
