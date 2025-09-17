const { spawn } = require('child_process');
const CRLF = '\r\n';

function sendMessage(proc, message) {
  const messageStr = JSON.stringify(message);
  const framedMessage = `Content-Length: ${Buffer.byteLength(messageStr, 'utf-8')}${CRLF}Content-Type: application/json${CRLF}${CRLF}${messageStr}`;
  proc.stdin.write(framedMessage);
}

async function readResponse(proc) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    let contentLength = -1;

    function onData(chunk) {
      buffer += chunk.toString('utf-8');

      while (true) {
        if (contentLength === -1) {
          const headerEndIndex = buffer.indexOf(CRLF + CRLF);
          if (headerEndIndex !== -1) {
            buffer
              .substring(0, headerEndIndex)
              .split(CRLF)
              .forEach((line) => {
                const [key, value] = line.split(':').map((s) => s.trim());
                if (key && value && key.toLowerCase() === 'content-length') {
                  contentLength = parseInt(value, 10);
                }
              });
            buffer = buffer.substring(headerEndIndex + CRLF.length * 2);
          } else {
            break;
          }
        }

        if (contentLength !== -1) {
          if (Buffer.byteLength(buffer, 'utf-8') >= contentLength) {
            const messageStr = buffer.substring(0, contentLength);
            buffer = buffer.substring(contentLength);
            proc.stdout.removeListener('data', onData);
            try {
              resolve(JSON.parse(messageStr));
            } catch (e) {
              reject(new Error(`Failed to parse JSON response: ${messageStr}`));
            }
            return;
          } else {
            break;
          }
        }
      }
    }

    proc.stdout.on('data', onData);
    setTimeout(() => reject(new Error('Test timed out after 10 seconds')), 10000);
  });
}

async function runTest() {
  console.log('Spouštím lokální test MCP serveru...');

  console.log('--- Krok 1: Sestavuji TypeScript projekt...');
  const build = spawn('npm', ['run', 'build'], { shell: true });
  build.stderr.on('data', (d) => process.stderr.write(`[BUILD] ${d}`));
  build.stdout.on('data', (d) => process.stdout.write(`[BUILD] ${d}`));

  await new Promise((resolve, reject) => {
    build.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Build selhal s kódem ${code}`));
    });
  });

  console.log('--- Krok 2: Spouštím MCP server (stdio)...');
  const serverProcess = spawn('node', ['dist/index.js']);

  let stderrOutput = '';
  serverProcess.stderr.on('data', (data) => {
    stderrOutput += data.toString();
    process.stderr.write(`[SERVER] ${data}`);
  });

  serverProcess.on('error', (err) => {
    console.error('Nepodařilo se spustit server:', err);
    process.exit(1);
  });

  console.log('--- Krok 3: Odesílám initialize požadavek...');
  // Krátké zpoždění, aby se server plně připojil
  await new Promise((r) => setTimeout(r, 150));
  const initializeRequest = {
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      clientInfo: { name: 'MCP Test Client', version: '0.1.0' },
      capabilities: {
        tools: {},
      },
    },
  };
  sendMessage(serverProcess, initializeRequest);

  console.log('--- Krok 4: Čekám na odpověď...');
  try {
    const response = await readResponse(serverProcess);
    console.log('--- Odpověď přijata ---');
    console.log(JSON.stringify(response, null, 2));

    let success = true;
    if (!stderrOutput.includes('--- MCP: Initialize request received ---')) {
      console.error('✖ SELHÁNÍ: Chybí diagnostický stderr log z initialize.');
      success = false;
    } else {
      console.log('✔ ÚSPĚCH: Diagnostický stderr log nalezen.');
    }

    if (
      response.result &&
      response.result.serverInfo &&
      response.result.serverInfo.name === 'marketing-miner-mcp'
    ) {
      console.log('✔ ÚSPĚCH: ServerInfo v initialize je správné.');
    } else {
      console.error('✖ SELHÁNÍ: ServerInfo v initialize je neplatné.');
      success = false;
    }

    if (success) console.log('\n🎉 Test prošel.');
    else console.error('\n🔥 Test selhal.');
  } catch (err) {
    console.error('✖ Chyba při čtení odpovědi:', err);
  } finally {
    serverProcess.kill();
  }
}

runTest();


