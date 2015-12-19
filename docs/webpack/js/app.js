require('bootstrap');

function selectText(text) {
  if (document.body.createTextRange) {
    let range = document.body.createTextRange();
    range.moveToElementText(text);
    range.select();
  } else if (window.getSelection) {
    let selection = window.getSelection();
    let range = document.createRange();
    range.selectNodeContents(text);
    selection.removeAllRanges();
    selection.addRange(range);
  }
}

function initDownloadButton() {
  let buttons = $('.download-btn');
  if (buttons.length <= 0) {
    return;
  }

  buttons.hide();
  $.ajax({
    method: 'GET',
    url: 'https://api.github.com/repos/lektor/lektor/releases',
    crossDomain: true
  }).then((releases) => {
    updateDownloadButtons(buttons.toArray(), releases);
  }, () => {
    buttons.show();
  });
}

function findBestTarget(assets) {
  let matcher = null;
  let note = null;
  if (navigator.platform.match(/^mac/i)) {
    matcher = /\.dmg$/;
    note = 'For OSX 10.9 and later.';
  }

  if (matcher != null) {
    for (let i = 0; i < assets.length; i++) {
      if (assets[i].name.match(matcher)) {
        return {
          url: assets[i].browser_download_url,
          note: note
        };
      }
    }
  }

  return null;
}

function updateDownloadButtons(buttons, releases) {
  let tag = releases[0].tag_name;
  let selectTarget = '/downloads/';
  let assetTarget = findBestTarget(releases[0].assets);

  buttons.forEach((button) => {
    let note = $('<div class="note"></div>').appendTo(button);
    let link = $('a', button);

    if (assetTarget) {
      link.attr('href', assetTarget.url);
      note.append($('<span></span>').text(assetTarget.note + ' '));
      note.append(
        $('<a>Other platforms</a>')
          .attr('href', selectTarget));
    } else {
      link.attr('href', selectTarget);
    }

    link.append($('<span class="version"></span>').text(tag));

    $(button).fadeIn('slow');
  });
}

function initInstallRow() {
  let code = $('.install-row pre');
  if (code.length > 0) {
    code.on('dblclick', function() {
      selectText(this);
    });
  }
}

$(function() {
  initDownloadButton();
  initInstallRow();
});
