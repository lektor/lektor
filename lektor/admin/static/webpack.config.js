var webpack = require('webpack')
var path = require('path')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')

module.exports = {
  mode: 'development',
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
  optimization: {
    splitChunks: {
      chunks: 'all',
      name: 'vendor'
      /*
      cacheGroups: {
        styles: {
          name: 'styles',
          test: /\.(le|c)ss$/,
          chunks: 'all',
          enforce: true
        }
      }
      */
    }
  },
  resolve: {
    modules: [
      '../node_modules'
    ],
    extensions: ['.jsx', '.js', '.json']
  },
  module: {
    rules: [
      {
        test: /\.jsx$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options: {
          presets: ['@babel/preset-react', '@babel/preset-env'],
          // plugins: ['transform-object-rest-spread'],
          cacheDirectory: true
        }
      },
      {
        test: /\.less$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader?sourceMap',
          'less-loader?sourceMap'
        ]
      },
      {
        test: /\.css$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader?sourceMap'
        ]
      },
      {
        test: /\.(ttf|eot|svg|woff2?)(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'file-loader'
      }
    ]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: '[name].css',
      chunkFilename: '[id].css'
    }),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery'
    })
  ],
  externals: {}
}
