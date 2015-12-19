'use strict';

var React = require('react');

var Component = require('../components/Component');
var dialogSystem = require('../dialogSystem');
var i18n = require('../i18n');


class SlideDialog extends Component {

  constructor(props) {
    super(props);
    this._onKeyPress = this._onKeyPress.bind(this);
  }

  componentDidMount() {
    super.componentDidMount();
    if (this.props.closeOnEscape) {
      window.addEventListener('keydown', this._onKeyPress);
    }
  }

  componentWillUnmount() {
    window.removeEventListener('keydown', this._onKeyPress);
    super.componentWillUnmount();
  }

  _onKeyPress(event) {
    if (event.which == 27 && this.props.closeOnEscape) {
      event.preventDefault();
      dialogSystem.dismissDialog();
    }
  }

  _onCloseClick(event) {
    event.preventDefault();
    dialogSystem.dismissDialog();
  }

  render() {
    var {children, title, hasCloseButton, className, ...props} = this.props;
    className = (className || '') + ' sliding-panel container';
    return (
      <div className={className} {...props}>
        <div className="col-md-6 col-md-offset-4">
          {hasCloseButton ?
            <a href="#" className="close-btn" onClick={
              this._onCloseClick.bind(this)}>{i18n.trans('CLOSE')}</a> : null}
          <h3>{title}</h3>
          {children}
        </div>
      </div>
    );
  }
}

SlideDialog.propTypes = {
  title: React.PropTypes.string,
  hasCloseButton: React.PropTypes.bool,
  closeOnEscape: React.PropTypes.bool
};


module.exports = SlideDialog;
