'use strict'

import React from 'react'
import Component from '../components/Component'
import SlideDialog from '../components/SlideDialog'
import utils from '../utils'
import i18n from '../i18n'
import dialogSystem from '../dialogSystem'


class Publish extends Component {

  constructor(props) {
    super(props);

    this.state = {
      servers: [],
      activeTarget: null,
      log: [],
      currentState: 'IDLE'
    };
  }

  componentDidMount() {
    super.componentDidMount();
    this.syncDialog();
  }

  componentWillUnmount() {
    super.componentWillUnmount();
  }

  componentWillReceiveProps(nextProps) {
    this.syncDialog();
  }

  preventNavigation() {
    return !this.isSafeToPublish();
  }

  syncDialog() {
    utils.loadData('/servers')
      .then((resp) => {
        this.setState({
          servers: resp.servers,
          activeTarget: resp.servers[0].id
        })
      });
  }

  isSafeToPublish() {
    return this.state.currentState === 'IDLE' ||
      this.state.currentState === 'DONE';
  }

  onPublish() {
    if (this.isSafeToPublish()) {
      this._beginBuild();
    }
  }

  onCancel() {
    dialogSystem.dismissDialog();
  }

  _beginBuild() {
    this.setState({
      log: [],
      currentState: 'BUILDING'
    });
    utils.apiRequest('/build', {
      method: 'POST'
    }).then((resp) => {
      this._beginPublish();
    });
  }

  _beginPublish() {
    this.setState({
      currentState: 'PUBLISH'
    });

    const es = new EventSource(utils.getApiUrl('/publish') +
      '?server=' + encodeURIComponent(this.state.activeTarget));
    es.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      if (data === null) {
        this.setState({
          currentState: 'DONE'
        });
        es.close();
      } else {
        this.setState({
          log: this.state.log.concat(data.msg)
        });
      }
    });
  }

  onSelectServer(event) {
    this.setState({
      activeTarget: event.target.value
    })
  }

  componentDidUpdate() {
    super.componentDidUpdate();
    const node = this.refs.log;
    if (node !== null) {
      node.scrollTop = node.scrollHeight;
    }
  }

  render() {
    const servers = this.state.servers.map((server) => {
      return (
        <option value={server.id} key={server.id}>
          {i18n.trans(server.name_i18n) + ' (' + server.short_target + ')'}
        </option>
      );
    });

    let progress = null;
    if (this.state.currentState !== 'IDLE') {
      progress = (
        <div>
          <h3>{this.state.currentState !== 'DONE'
            ? i18n.trans('CURRENTLY_PUBLISHING')
            : i18n.trans('PUBLISH_DONE')}</h3>
          <pre>{i18n.trans('STATE') + ': ' +
            i18n.trans('PUBLISH_STATE_' + this.state.currentState)}</pre>
          <pre ref="log" className="build-log">{this.state.log.join('\n')}</pre>
        </div>
      );
    }

    return (
      <SlideDialog
        hasCloseButton={false}
        closeOnEscape={true}
        title={i18n.trans('PUBLISH')}>
        <p>{i18n.trans('PUBLISH_NOTE')}</p>
        <dl>
          <dt>{i18n.trans('PUBLISH_SERVER')}</dt>
          <dd><div className="input-group">
            <select value={this.state.activeTarget}
              onChange={this.onSelectServer.bind(this)}
              className="form-control">{servers}</select>
          </div></dd>
        </dl>
        <div className="actions">
          <button type="submit" className="btn btn-primary"
            disabled={!this.isSafeToPublish()}
            onClick={this.onPublish.bind(this)}>{i18n.trans('PUBLISH')}</button>
          <button type="submit" className="btn btn-default"
            disabled={!this.isSafeToPublish()}
            onClick={this.onCancel.bind(this)}>{i18n.trans(
              this.state.currentState === 'DONE' ? 'CLOSE' : 'CANCEL')}</button>
        </div>
        {progress}
      </SlideDialog>
    );
  }
}

export default Publish
