import jQuery from 'jquery'

export function isValidUrl (url) {
  return !!url.match(/^(https?|ftp):\/\/\S+$/)
}

function stripLeadingSlash (string) {
  return string.match(/^\/*(.*?)$/)[1]
}

function stripTrailingSlash (string) {
  return string.match(/^(.*?)\/*$/)[1]
}

function addToSet (originalSet, value) {
  for (let i = 0; i < originalSet.length; i++) {
    if (originalSet[i] === value) {
      return originalSet
    }
  }
  const rv = originalSet.slice()
  rv.push(value)
  return rv
}

function removeFromSet (originalSet, value) {
  let rv = null
  let off = 0
  for (let i = 0; i < originalSet.length; i++) {
    if (originalSet[i] === value) {
      if (rv === null) {
        rv = originalSet.slice()
      }
      rv.splice(i - (off++), 1)
    }
  }
  return (rv === null) ? originalSet : rv
}

const utils = {
  getCanonicalUrl (localPath) {
    return $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
      '/' + stripLeadingSlash(localPath)
  },

  flipSetValue (originalSet, value, isActive) {
    if (isActive) {
      return addToSet(originalSet || [], value)
    } else {
      return removeFromSet(originalSet || [], value)
    }
  },

  urlPathsConsideredEqual (a, b) {
    if ((a == null) || (b == null)) {
      return false
    }
    return stripTrailingSlash(a) === stripTrailingSlash(b)
  },

  fsPathFromAdminObservedPath (adminPath) {
    const base = $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1]
    if (adminPath.substr(0, base.length) !== base) {
      return null
    }
    return '/' + adminPath.substr(base.length).match(/^\/*(.*?)\/*$/)[1]
  },

  getParentFsPath (fsPath) {
    return fsPath.match(/^(.*?)\/([^/]*)$/)[1]
  },

  getApiUrl (url) {
    return $LEKTOR_CONFIG.admin_root + '/api' + url
  },

  loadData (url, params, options, createPromise) {
    options = options || {}
    return createPromise((resolve, reject) => {
      jQuery.ajax({
        url: utils.getApiUrl(url),
        data: params,
        method: options.method || 'GET'
      }).done((data) => {
        resolve(data)
      }).fail(() => {
        reject({
          code: 'REQUEST_FAILED'
        })
      })
    })
  },

  apiRequest (url, options, createPromise) {
    options = options || {}
    options.url = utils.getApiUrl(url)
    if (options.json !== undefined) {
      options.data = JSON.stringify(options.json)
      options.contentType = 'application/json'
      delete options.json
    }
    if (!options.method) {
      options.method = 'GET'
    }

    return createPromise((resolve, reject) => {
      jQuery.ajax(options)
        .done((data) => {
          resolve(data)
        })
        .fail(() => {
          reject({
            code: 'REQUEST_FAILED'
          })
        })
    })
  },

  fsToUrlPath (fsPath) {
    let segments = fsPath.match(/^\/*(.*?)\/*$/)[1].split('/')
    if (segments.length === 1 && segments[0] === '') {
      segments = []
    }
    segments.unshift('root')
    return segments.join(':')
  },

  urlToFsPath (urlPath) {
    const segments = urlPath.match(/^:*(.*?):*$/)[1].split(':')
    if (segments.length < 1 || segments[0] !== 'root') {
      return null
    }
    segments[0] = ''
    return segments.join('/')
  },

  urlPathToSegments (urlPath) {
    if (!urlPath) {
      return null
    }
    const rv = urlPath.match(/^:*(.*?):*$/)[1].split('/')
    if (rv.length >= 1 && rv[0] === 'root') {
      return rv.slice(1)
    }
    return null
  },

  getPlatform () {
    if (navigator.appVersion.indexOf('Win') !== -1) {
      return 'windows'
    } else if (navigator.appVersion.indexOf('Mac') !== -1) {
      return 'mac'
    } else if (navigator.appVersion.indexOf('X11') !== -1 ||
        navigator.appVersion.indexOf('Linux') !== -1) {
      return 'linux'
    }
    return 'other'
  },

  isMetaKey (event) {
    if (utils.getPlatform() === 'mac') {
      return event.metaKey
    } else {
      return event.ctrlKey
    }
  }
}

export default utils
