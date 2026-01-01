const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: './src/react/Chatbot.jsx',
  output: {
    path: path.resolve(__dirname, 'frontend/dist'),
    filename: 'chatbot-react.js',
    library: 'ChatbotReact',
    libraryTarget: 'umd',
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
          },
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  resolve: {
    extensions: ['.js', '.jsx'],
  },
  externals: {
    react: 'React',
    'react-dom': 'ReactDOM',
    // react-markdown will be bundled, not externalized
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './frontend/index.html',
      filename: '../index.html',
      inject: false,
    }),
  ],
};

