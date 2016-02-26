'use strict';

var React = require('react');
var Router = require('react-router');

var Component = require('../components/Component');
var Link = require('../components/Link');
var utils = require('../utils');

class UsersPage extends Component {
  constructor(props) {
    super(props);

    this.state = this._getInitialState();
  }

  _getInitialState() {
    return {data: {users: []}};
  }

  refreshState() {
    utils.request('/users').then((resp) => {
      this.setState({data: resp});
    });
  }

  componentDidMount() {
    this.refreshState();
  }

  onDeleteUser(e) {
    var username = e.target.dataset.username || e.target.parentElement.dataset.username;

    utils.request('/users/delete', {
      json: {username: username},
      method: 'POST'
    }).then((resp) => {
      this.refreshState();
    });
  }

  onResetPassword(e) {
    var username = e.target.dataset.username || e.target.parentElement.dataset.username;

    utils.request('/users/reset', {
      json: {username: username},
      method: 'POST'
    }).then((resp) => {
      this.props.history.pushState(
        null, '/admin/users/set-password-link', {username: username, link: resp.link, new_user: false});
    });
  }

  renderUsers() {
    var users = this.state.data.users.map((user, i) => {
      return (
        <tr key={i}>
          <td className="username">{user}</td>
          <td>
            <button className="btn btn-default" data-username={user} onClick={this.onDeleteUser.bind(this)}>
              <span title="Delete" className="fa fa-ban fa-fw"></span>
            </button>
          </td>
          <td>
            <button className="btn btn-default" data-username={user} onClick={this.onResetPassword.bind(this)}>
              <span title="Reset Password" className="fa fa-unlock-alt fa-fw"></span>
            </button>
          </td>
        </tr>
      );
    });

    return (
    <table>
      <thead><tr><th>Username</th></tr></thead>
      <tbody>{users}</tbody>
    </table>
    );
  }

  render() {
    return (
      <div>
        <h1>Users</h1>
        <Link to="/admin/users/add-user">
          <span className="fa fa-user-plus fa-fw"></span>Add a user
        </Link>
        {this.renderUsers()}
      </div>
    );
  }
}

module.exports = UsersPage;
