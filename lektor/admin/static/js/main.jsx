'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var {Router, Route, IndexRoute} = require('react-router');
var Component = require('./components/Component');
var i18n = require('./i18n');
var {useBeforeUnload} = require('history');
var createBrowserHistory = require('history/lib/createBrowserHistory');

require('bootstrap');
require('./bootstrap-extras');
require('font-awesome/css/font-awesome.css');

// polyfill for internet explorer
require('native-promise-only');
require('event-source-polyfill');

i18n.currentLanguage = $LEKTOR_CONFIG.lang;

class BadRoute extends Component {

  render() {
    return (
      <div>
        <h2>Nothing to see here</h2>
        <p>There is really nothing to see here.</p>
      </div>
    );
  }
}

BadRoute.contextTypes = {
  router: React.PropTypes.func
};

var routes = (function() {
  // route targets
  var App = require('./views/App');
  var Dash = require('./views/Dash');
  var EditPage = require('./views/EditPage');
  var DeletePage = require('./views/DeletePage');
  var PreviewPage = require('./views/PreviewPage');
  var AddChildPage = require('./views/AddChildPage');
  var AddAttachmentPage = require('./views/AddAttachmentPage');

  // route setup
  return (
    <Route name="app" path={$LEKTOR_CONFIG.admin_root} component={App}>
      <Route name="edit" path=":path/edit" component={EditPage}/>
      <Route name="delete" path=":path/delete" component={DeletePage}/>
      <Route name="preview" path=":path/preview" component={PreviewPage}/>
      <Route name="add-child" path=":path/add-child" component={AddChildPage}/>
      <Route name="upload" path=":path/upload" component={AddAttachmentPage}/>
      <IndexRoute component={Dash}/>
      <route path="*" component={BadRoute}/>
    </Route>
  );
})();

var dash = document.getElementById('dash')
if (dash) {
  ReactDOM.render((
    <Router history={useBeforeUnload(createBrowserHistory)()}>
      {routes}
    </Router>
  ), dash);
}
