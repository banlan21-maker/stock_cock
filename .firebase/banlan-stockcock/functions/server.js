const { onRequest } = require('firebase-functions/v2/https');
  const server = import('firebase-frameworks');
  exports.ssrbanlanstockcock = onRequest({"region":"us-central1","timeoutSeconds":60,"minInstances":0}, (req, res) => server.then(it => it.handle(req, res)));
  