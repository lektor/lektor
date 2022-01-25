const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
  mode: "development",
  entry: {
    app: "./js/main.tsx",
  },
  output: {
    path: path.join(__dirname, "gen"),
    publicPath: "./",
  },
  devtool: "source-map",
  optimization: {
    splitChunks: { chunks: "all", name: "vendor" },
  },
  resolve: {
    modules: ["../node_modules"],
    extensions: [".tsx", ".ts", "..."],
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
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
        test: /\.scss$/,
        use: [MiniCssExtractPlugin.loader, "css-loader", "sass-loader"],
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, "css-loader"],
      },
      {
        test: /\.(ttf|eot|svg|woff2?)(\?v=\d+\.\d+\.\d+)?$/,
        type: "asset",
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
