// craco.config.js
const path = require("path");
require("dotenv").config();

// Check if we're in development/preview mode (not production build)
// Craco sets NODE_ENV=development for start, NODE_ENV=production for build
const isDevServer = process.env.NODE_ENV !== "production";

// Environment variable overrides
const config = {
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
};

function makeDevServerV5Compatible(devServerConfig) {
  const {
    https,
    onAfterSetupMiddleware,
    onBeforeSetupMiddleware,
    onListening,
    setupMiddlewares,
    ...compatibleConfig
  } = devServerConfig;

  compatibleConfig.server =
    typeof https === "object"
      ? { type: "https", options: https }
      : https
        ? "https"
        : "http";
  compatibleConfig.headers = {
    ...compatibleConfig.headers,
    "Cross-Origin-Resource-Policy": "same-origin",
  };

  if (onBeforeSetupMiddleware || setupMiddlewares) {
    compatibleConfig.setupMiddlewares = (middlewares, devServer) => {
      if (onBeforeSetupMiddleware) {
        onBeforeSetupMiddleware(devServer);
      }

      return setupMiddlewares
        ? setupMiddlewares(middlewares, devServer)
        : middlewares;
    };
  }

  compatibleConfig.onListening = (devServer) => {
    devServer.close ??= (callback) => devServer.stopCallback(callback);

    if (onListening) {
      onListening(devServer);
    }
    if (onAfterSetupMiddleware) {
      onAfterSetupMiddleware(devServer);
    }
  };

  return compatibleConfig;
}

// Conditionally load health check modules only if enabled
let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

// ---------------------------------------------------------------------------
// Guarda de build: NUNCA embutir a chave da API do pipeline num bundle publico
// ---------------------------------------------------------------------------
// `REACT_APP_PIPELINE_API_KEY` e o segredo compartilhado que protege TODAS as
// rotas do backend do pipeline. O Create React App substitui `REACT_APP_*` no
// bundle em tempo de build — isto e, a chave sai em texto claro num arquivo .js
// servido publicamente. Qualquer visitante abriria o bundle, leria a chave e
// teria acesso total ao anotador: gerar, editar e apagar itens.
//
// O painel do pipeline e uma ferramenta INTERNA. Publica-lo abertamente exige
// antes uma camada de autenticacao propria (sessao por usuario), que ainda nao
// existe. Ate la, uma build de producao com a chave presente e recusada aqui.
//
// Para operar hoje, escolha um destes:
//   1. Nao exponha o painel a internet publica — rode-o localmente contra o
//      backend publicado, ou por tras da autenticacao da plataforma de hosting
//      (Cloudflare Access, autenticacao de rede privada, VPN).
//   2. Publique-o com PIPELINE_UI_PUBLICA=true e ciente do risco, apenas se o
//      backend estiver inacessivel a partir da internet.
if (process.env.NODE_ENV === "production" && process.env.REACT_APP_PIPELINE_API_KEY) {
  if (process.env.PIPELINE_UI_PUBLICA !== "true") {
    throw new Error(
      "\n\n[build recusada] REACT_APP_PIPELINE_API_KEY seria embutida no bundle " +
        "publico, expondo o segredo que protege todas as rotas do pipeline.\n" +
        "Ver o comentario em pipeline/frontend/craco.config.js para as opcoes.\n"
    );
  }
  console.warn(
    "\n[AVISO] Build de producao com a chave da API embutida (PIPELINE_UI_PUBLICA=true).\n" +
      "So faca isso se o backend do pipeline NAO estiver acessivel pela internet publica.\n"
  );
}

let webpackConfig = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {

      // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
        ],
      };

      // Add health check plugin to webpack if enabled
      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }
      return webpackConfig;
    },
  },
};

webpackConfig.devServer = (devServerConfig) => {
  // Add health check endpoints if enabled
  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      // Call original setup if exists
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      // Setup health endpoints
      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

const configureDevServer = webpackConfig.devServer;
webpackConfig.devServer = (devServerConfig) =>
  makeDevServerV5Compatible(configureDevServer(devServerConfig));

module.exports = webpackConfig;
