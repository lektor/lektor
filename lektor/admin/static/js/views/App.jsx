'use strict';

var React = require('react');

var BreadCrumbs = require('../components/BreadCrumbs');
var Sidebar = require('../components/Sidebar');
var Component = require('../components/Component');
var DialogSlot = require('../components/DialogSlot');
var ServerStatus = require('../components/ServerStatus');
var dialogSystem = require('../dialogSystem');
var {DialogChangedEvent} = require('../events');
var hub = require('../hub');


class App extends Component {

  render() {
    return (
      <div className="application">
        <ServerStatus/>
        <header>
          <BreadCrumbs {...this.getRoutingProps()}>
            <button type="button" className="navbar-toggle"
                data-toggle="offcanvas"
                data-target=".sidebar-block">
              <span className="sr-only">Toggle navigation</span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
            </button>
          </BreadCrumbs>
        </header>
        <div className="editor container">
          <DialogSlot {...this.getRoutingProps()}/>
          <div className="sidebar-block block-offcanvas block-offcanvas-left">
            <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
              <Sidebar {...this.getRoutingProps()}/>
            </nav>
            <div className="view col-md-10 col-sm-9">
              {this.props.children}
            </div>
          </div>
        </div>
      </div>
    );
  }
}

module.exports = App;
