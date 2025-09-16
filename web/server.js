import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const host = 'xx.xx.xx.x';
const port = 8081;
const inferport = 8013;
const voiceport = 9000;

app.use(express.static(path.join(__dirname, '')));

app.use('/api', createProxyMiddleware({
  target: `http://${host}:${inferport}`,
  pathRewrite: {'^/api': ''},
  changeOrigin: true,
  secure: false
}));

app.use('/voice', createProxyMiddleware({
  target: `http://${host}:${voiceport}`,
  pathRewrite: {'^/voice': ''},
  changeOrigin: true,
  secure: false
}));

const sslCertPath = path.resolve(__dirname, 'cert.pem');
const sslKeyPath = path.resolve(__dirname, 'key.pem');

const options = {
  key: fs.existsSync(sslKeyPath) ? fs.readFileSync(sslKeyPath) : undefined,
  cert: fs.existsSync(sslCertPath) ? fs.readFileSync(sslCertPath) : undefined,
  minVersion: 'TLSv1.2',
  ciphers: [
    'ECDHE-ECDSA-AES128-GCM-SHA256',
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-ECDSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES256-GCM-SHA384',
    'ECDHE-ECDSA-CHACHA20-POLY1305',
    'ECDHE-RSA-CHACHA20-POLY1305',
    'DHE-RSA-AES128-GCM-SHA256',
    'DHE-RSA-AES256-GCM-SHA384'
  ].join(':'),
};

https.createServer(options, app).listen(port, host, () => {
  console.log(`Server running at https://${host}:${port}`);
});
