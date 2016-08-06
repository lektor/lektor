'use strict'

import qs from 'querystring'
import React from 'react'
import Router from 'react-router'
import RecordComponent from '../components/RecordComponent'
import hub from '../hub'
import {AttachmentsChangedEvent} from '../events'
import utils from '../utils'
import i18n from '../i18n'
import widgets from '../widgets'


function getGoodDefaultModel(models) {
  if (models.page !== undefined) {
    return 'page';
  }
  const choices = Object.keys(models);
  choices.sort();
  return choices[0];
}


class AddAttachmentPage extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      newAttachmentInfo: null,
      currentFiles: [],
      isUploading: false,
      currentProgress: 0
    }
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentWillReceiveProps(nextProps) {
    this.syncDialog();
  }

  syncDialog() {
    utils.loadData('/newattachment', {path: this.getRecordPath()})
      .then((resp) => {
        this.setState({
          newAttachmentInfo: resp
        });
      });
  }

  uploadFile(event) {
    this.refs.file.click();
  }

  onUploadProgress(event) {
    const newProgress = Math.round((event.loaded * 100) / event.total)
    if (newProgress != this.state.currentProgress) {
      this.setState({
        currentProgress: newProgress
      });
    }
  }

  onUploadComplete(resp, event) {
    this.setState({
      isUploading: false,
      newProgress: 100
    }, () => {
      hub.emit(new AttachmentsChangedEvent({
        recordPath: this.getRecordPath(),
        attachmentsAdded: resp.buckets.map((bucket) => {
          return bucket.stored_filename;
        })
      }));
    });
  }

  onFileSelected(event) {
    if (this.state.isUploading) {
      return;
    }

    const files = this.refs.file.files;
    this.setState({
      currentFiles: Array.prototype.slice.call(files, 0),
      isUploading: true
    });

    const formData = new FormData();
    formData.append('path', this.getRecordPath());

    for (let i = 0; i < files.length; i++) {
      formData.append('file', files[i], files[i].name);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', utils.getApiUrl('/newattachment'));
    xhr.onload = (event) => {
      this.onUploadComplete(JSON.parse(xhr.responseText), event);
    };
    xhr.upload.onprogress = (event) => {
      this.onUploadProgress(event);
    };
    xhr.send(formData);
  }

  renderCurrentFiles() {
    const files = this.state.currentFiles.map((file) => {
      return (
        <li key={file.name}>{file.name} ({file.type})</li>
      );
    });
    return <ul>{files}</ul>;
  }

  render() {
    const nai = this.state.newAttachmentInfo;

    if (!nai) {
      return null;
    }

    return (
      <div>
        <h2>{i18n.trans('ADD_ATTACHMENT_TO').replace('%s', nai.label)}</h2>
        <p>{i18n.trans('ADD_ATTACHMENT_NOTE')}</p>
        {this.renderCurrentFiles()}
        <p>{i18n.trans('PROGRESS')}: {this.state.currentProgress}%</p>
        <input type="file" ref="file" multiple={true}
          style={{display: 'none'}} onChange={this.onFileSelected.bind(this)} />
        <div className="actions">
          <button className="btn btn-primary" onClick={this.uploadFile.bind(this)}>{
            i18n.trans('UPLOAD')}</button>
        </div>
      </div>
    );
  }
}

export default AddAttachmentPage
