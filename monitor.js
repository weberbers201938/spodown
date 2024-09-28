const currentUrl = `https://replit.com/@${process.env.REPL_OWNER}/${process.env.REPL_SLUG}`;
const fs = require('fs');
const path = require('path');
const freeport = require('freeport');
const ProxyChain = require('proxy-chain');
const puppeteer = require('puppeteer-core');
const { exec } = require('node:child_process');
const { promisify } = require('node:util');

const screenshotPath = path.join(__dirname, 'screenshot.jpg');

let browser, page, newTab;

async function startBrowser() {
  try {
    const { stdout: chromiumPath } = await promisify(exec)("which chromium");

    browser = await puppeteer.launch({
      headless: false,
      executablePath: chromiumPath.trim(),
      ignoreHTTPSErrors: true,
      args: [
        '--ignore-certificate-errors',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-dev-shm-usage',
        '--no-sandbox'
      ]
    });

    page = await browser.newPage();
    await page.setUserAgent("Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_7;en-us) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Safari/530.17");

    const cookies = JSON.parse(fs.readFileSync('replit.json', 'utf8'));
    await page.setCookie(...cookies);

    await page.goto(currentUrl, { waitUntil: 'networkidle2', timeout: 0 });

    newTab = await browser.newPage();
    await newTab.setUserAgent("Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_7;en-us) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Safari/530.17");
    await newTab.setCookie(...cookies);
    await newTab.goto(currentUrl, { waitUntil: 'networkidle2', timeout: 0 });

    await page.screenshot({ path: screenshotPath, type: 'jpeg' });

    console.log('Browser is running. Press Ctrl+C to exit.');

    // Keep the process alive
    setInterval(async () => {
      try {
        console.log('Refreshing page to keep the session alive...');
        await page.reload({ waitUntil: 'networkidle2', timeout: 0 });
      } catch (err) {
        console.error('Error refreshing page:', err);
      }
    }, 300000); // Refresh every 5 minutes

  } catch (error) {
    console.error('Error starting browser:', error);
    console.log('Retrying in 10 seconds...');
    setTimeout(startBrowser, 10000); // Retry after 10 seconds
  }
}

async function run() {
  freeport(async (err, proxyPort) => {
    if (err) {
      console.error('Error finding free port:', err);
      return;
    }

    const proxyServer = new ProxyChain.Server({ port: proxyPort });

    proxyServer.listen(async () => {
      await startBrowser();
    });
  });
}

run();
