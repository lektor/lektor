'use strict';

var React = require('react');
var Router = require("react-router");

var Component = require('../components/Component');
var dialogSystem = require('../dialogSystem');
var {DialogChangedEvent} = require('../events');
var hub = require('../hub');


class DialogSlot extends Component {

  constructor(props) {
    super(props);
    this.state = {
      currentDialog: null,
      currentDialogOptions: null
    };
    this.onDialogChanged = this.onDialogChanged.bind(this);
  }

  componentDidMount() {
    super.componentDidMount();
    hub.subscribe(DialogChangedEvent, this.onDialogChanged);
  }

  componentWillUnmount() {
    super.componentWillUnmount();
    hub.unsubscribe(DialogChangedEvent, this.onDialogChanged);
  }

  onDialogChanged(event) {
    this.setState({
      currentDialog: event.dialog,
      currentDialogOptions: event.dialogOptions || {}
    });
  }

  initDialogInstance(dialog) {
    dialogSystem.notifyDialogInstance(dialog);
    window.scrollTo(0, 0);
  }

  render() {
    var dialog = null;
    if (this.state.currentDialog) {
      dialog = <this.state.currentDialog
        ref={(ref) => this.initDialogInstance(ref)}
        {...this.getRoutingProps()}
        {...this.state.currentDialogOptions}
      />;
    } else {
      dialogSystem.notifyDialogInstance(null);
    }

    if (!dialog) {
      return null;
    }

    return (
      <div className="dialog-slot">
        {dialog}
        <div className="interface-protector"></div>
      </div>
    );
  }
}

module.exports = DialogSlot;
