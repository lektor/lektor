var webpack = require('webpack')
var path = require('path')
var ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
  entry: {
    'app': './js/main.jsx',
    'styles': './less/main.less',
    'vendor': [
      'jquery',
      'native-promise-only',
      'querystring',
      'bootstrap',
      'react',
      'react-dom',
      'react-addons-update',
      'react-router'
    ]
  },
  output: {
    path: path.join(__dirname, '/gen'),
    filename: '[name].js'
  },
  devtool: 'source-map',
  resolve: {
    modules: [
      '../node_modules'
    ],
    extensions: ['.jsx', '.js', '.json']
  },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options: {
          presets: ['react', 'es2015'],
          plugins: ['transform-object-rest-spread'],
          cacheDirectory: true
        }
      },
      {
        test: /\.less$/,
        loader: ExtractTextPlugin.extract({
          use: 'css-loader!less-loader?sourceMap',
          fallback: 'style-loader?sourceMap'
        })
      },
      {
        test: /\.css$/,
        loader: ExtractTextPlugin.extract({
          use: 'css-loader?sourceMap',
          fallback: 'style-loader?sourceMap'
        })
      },
      {
        test: /\.json$/,
        loader: 'json-loader'
      },
      {
        test: /\.(ttf|eot|svg|woff2?)(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'file-loader'
      }
    ]
  },
  plugins: [
    new webpack.optimize.CommonsChunkPlugin({
      name: 'vendor',
      filename: 'vendor.js'
    }),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery'
    }),
    new ExtractTextPlugin('styles.css', {
      allChunks: true
    })
  ],
  externals: {}
}
