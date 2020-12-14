const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
  mode: "development",
  entry: {
    app: "./js/main.jsx",
    styles: "./less/main.less",
  },
  output: {
    path: path.join(__dirname, "/gen"),
    publicPath: "./",
    filename: "[name].js",
  },
  devtool: "source-map",
  optimization: {
    splitChunks: {
      chunks: "all",
      name: "vendor",
    },
  },
  resolve: {
    modules: ["../node_modules"],
    extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
  },
  module: {
    rules: [
      {
        test: /\.(j|t)sx?$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: {
          presets: [
            "@babel/preset-env",
            "@babel/preset-react",
            "@babel/preset-typescript",
          ],
          cacheDirectory: true,
        },
      },
      {
        test: /\.less$/,
        use: [
          MiniCssExtractPlugin.loader,
          "css-loader?sourceMap",
          "less-loader?sourceMap",
        ],
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, "css-loader?sourceMap"],
      },
      {
        test: /\.(ttf|eot|svg|woff2?)(\?v=\d+\.\d+\.\d+)?$/,
        loader: "file-loader",
      },
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: "[name].css",
      chunkFilename: "[id].css",
    }),
  ],
};
