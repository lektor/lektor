'use strict'

import qs from 'querystring'
import React from 'react'
import Router from 'react-router'
import RecordComponent from '../components/RecordComponent'
import i18n from '../i18n'
import userLabel from '../userLabel'
import utils from '../utils'
import widgets from '../widgets'


function getGoodDefaultModel(models) {
  if (models.page !== undefined) {
    return 'page';
  }
  const choices = Object.keys(models)
  choices.sort();
  return choices[0];
}


class AddChildPage extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      newChildInfo: null,
      id: undefined,
      selectedModel: null
    }
  }

  componentDidMount() {
    super.componentDidMount();
    this.syncDialog();
  }

  componentWillReceiveProps(nextProps) {
    super.componentWillReceiveProps(nextProps);
    this.syncDialog();
  }

  syncDialog() {
    utils.loadData('/newrecord', {path: this.getRecordPath()})
      .then((resp) => {
        let selectedModel = resp.implied_model;
        if (!selectedModel) {
          selectedModel = getGoodDefaultModel(resp.available_models);
        }

        this.setState({
          newChildInfo: resp,
          id: undefined,
          primary: undefined,
          selectedModel: selectedModel
        });
      });
  }

  onValueChange(id, value) {
    const obj = {};
    obj[id] = value;
    this.setState(obj);
  }

  getAvailableModels() {
    const rv = [];
    for (const key in this.state.newChildInfo.available_models) {
      const model = this.state.newChildInfo.available_models[key];
      rv.push(model);
    }
    rv.sort((a, b) => {
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
    });
    return rv;
  }

  onModelSelected(event) {
    this.setState({
      selectedModel: event.target.value
    });
  }

  getImpliedId() {
    return utils.slugify(this.state.primary || '').toLowerCase();
  }

  getPrimaryField() {
    return this.state.newChildInfo.available_models[
      this.state.selectedModel].primary_field;
  }

  createRecord() {
    function errMsg(text) {
      alert(i18n.trans('ERROR_PREFIX') + text);
    }

    const id = this.state.id || this.getImpliedId();
    if (!id) {
      errMsg(i18n.trans('ERROR_NO_ID_PROVIDED'));
      return;
    }

    const data = {};
    const params = {id: id, path: this.getRecordPath(), data: data};
    if (!this.state.newChildInfo.implied_model) {
      data['_model'] = this.state.selectedModel;
    }
    const primaryField = this.getPrimaryField();
    if (primaryField) {
      data[primaryField.name] = this.state.primary;
    }

    utils.apiRequest('/newrecord', {json: params, method: 'POST'})
      .then((resp) => {
        if (resp.exists) {
          errMsg(i18n.trans('ERROR_PAGE_ID_DUPLICATE').replace('%s', id));
        } else if (!resp.valid_id) {
          errMsg(i18n.trans('ERROR_INVALID_ID').replace('%s', id));
        } else {
          const urlPath = this.getUrlRecordPathWithAlt(resp.path);
          this.transitionToAdminPage('.edit', {path: urlPath});
        }
      });
  }

  renderFields() {
    const fields = [];

    if (!this.state.newChildInfo.implied_model) {
      const choices = this.getAvailableModels().map((model) => {
        return (
          <option value={model.id} key={model.id}>{i18n.trans(model.name_i18n)}</option>
        );
      });
      fields.push(
        <div className="row" key="_model">
          <div className="field-box col-md-12">
            <dl className="field">
              <dt>{i18n.trans('MODEL')}</dt>
              <dd><select value={this.state.selectedModel}
                  className="form-control"
                  onChange={this.onModelSelected.bind(this)}>
                {choices}
              </select></dd>
            </dl>
          </div>
        </div>
      );
    }

    const addField = (id, field, placeholder) => {
      let value = this.state[id];
      const Widget = widgets.getWidgetComponentWithFallback(field.type);
      if (Widget.deserializeValue) {
        value = Widget.deserializeValue(value, field.type);
      }
      fields.push(
        <div className="row field-row" key={field.name}>
          <div className="field-box col-md-12">
            <dl className="field">
              <dt>{userLabel.format(field.label_i18n || field.label)}</dt>
              <dd><Widget
                value={value}
                placeholder={placeholder}
                onChange={this.onValueChange.bind(this, id)}
                type={field.type}
              /></dd>
            </dl>
          </div>
        </div>
      );
    };

    const primaryField = this.getPrimaryField();
    if (primaryField) {
      addField('primary', primaryField);
    }

    addField('id', {
      name: '_id',
      label: i18n.trans('ID'),
      type: {name: 'slug', widget: 'slug'}
    }, this.getImpliedId());

    return fields;
  }

  render() {
    const nci = this.state.newChildInfo;

    if (!nci) {
      return null;
    }

    return (
      <div className="edit-area">
        <h2>{i18n.trans('ADD_CHILD_PAGE_TO').replace(
          '%s', this.state.newChildInfo.label)}</h2>
        <p>{i18n.trans('ADD_CHILD_PAGE_NOTE')}</p>
        {this.renderFields()}
        <div className="actions">
          <button className="btn btn-primary" onClick={
            this.createRecord.bind(this)}>{i18n.trans('CREATE_CHILD_PAGE')}</button>
        </div>
      </div>
    );
  }
}

export default AddChildPage
