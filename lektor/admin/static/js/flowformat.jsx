import metaformat from './metaformat'
import widgets from './widgets'

/* circular references require us to do this */
const getWidgetComponent = (type) => {
  return widgets.getWidgetComponent(type)
}

const parseFlowFormat = (value) => {
  let blocks = []
  let buf = []
  let lines = value.split(/\r?\n/)
  let block = null

  for (const line of lines) {
    // leading whitespace is ignored.
    if (block === null && line.match(/^\s*$/)) {
      continue
    }

    const blockStart = line.match(/^####\s*([^#]*?)\s*####\s*$/)
    if (!blockStart) {
      if (block === null) {
        // bad format :(
        return null
      }
    } else {
      if (block !== null) {
        blocks.push([block, buf])
        buf = []
      }
      block = blockStart[1]
      continue
    }

    buf.push(line.replace(/^#####(.*?)#####$/, '####$1####'))
  }

  if (block !== null) {
    blocks.push([block, buf])
  }

  return blocks
}

const serializeFlowFormat = (blocks) => {
  let rv = []
  blocks.forEach((block) => {
    const [blockName, lines] = block
    rv.push('#### ' + blockName + ' ####\n')
    lines.forEach((line) => {
      rv.push(line.replace(/^(####(.*)####)(\r?\n)?$/, '#$1#$3'))
    })
  })

  rv = rv.join('')

  /* we need to chop of the last newline if it exists because this would
     otherwise add a newline to the last block.  This is just a side effect
     of how we serialize the meta format internally */
  if (rv[rv.length - 1] === '\n') {
    rv = rv.substr(0, rv.length - 1)
  }

  return rv
}

const deserializeFlowBlock = (flowBlockModel, lines, localId) => {
  let data = {}
  let rawData = {}

  metaformat.tokenize(lines).forEach((item) => {
    const [key, lines] = item
    const value = lines.join('')
    rawData[key] = value
  })

  flowBlockModel.fields.forEach((field) => {
    let value = rawData[field.name] || ''
    const Widget = getWidgetComponent(field.type)
    if (!value && field['default']) {
      value = field['default']
    }
    if (Widget && Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type)
    }
    data[field.name] = value
  })

  return {
    localId: localId || null,
    flowBlockModel: flowBlockModel,
    data: data
  }
}

const serializeFlowBlock = (flockBlockModel, data) => {
  let rv = []
  flockBlockModel.fields.forEach((field) => {
    const Widget = getWidgetComponent(field.type)
    if (Widget === null) {
      return
    }

    let value = data[field.name]
    if (value === undefined || value === null) {
      return
    }

    if (Widget.serializeValue) {
      value = Widget.serializeValue(value, field.type)
    }

    rv.push([field.name, value])
  })
  return metaformat.serialize(rv)
}

export default {
  parseFlowFormat: parseFlowFormat,
  serializeFlowFormat: serializeFlowFormat,
  deserializeFlowBlock: deserializeFlowBlock,
  serializeFlowBlock: serializeFlowBlock
}
