const webpack = require('webpack')
const path = require('path')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')

module.exports = {
  mode: 'development',
  entry: {
    app: './js/main.jsx',
    styles: './less/main.less',
    vendor: [
      'jquery',
      'bootstrap',
      'react',
      'react-dom',
      'react-router-dom'
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
