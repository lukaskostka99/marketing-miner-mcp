#!/usr/bin/env node
"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const sse_js_1 = require("@modelcontextprotocol/sdk/server/sse.js");
const http_1 = __importDefault(require("http"));
const url_1 = require("url");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const axios_1 = __importDefault(require("axios"));
// Marketing Miner API konfigurace
const API_BASE = 'https://profilers-api.marketingminer.com';
const SUGGESTIONS_TYPES = ['questions', 'new', 'trending'];
const LANGUAGES = ['cs', 'sk', 'pl', 'hu', 'ro', 'gb', 'us'];
// Získání API tokenu z různých zdrojů
function getApiToken() {
    const possibleKeys = [
        'MARKETING_MINER_API_TOKEN',
        'MARKETING_MINER_API_KEY',
        'MARKETING_MINER_TOKEN',
        'MM_API_TOKEN',
        'MM_API_KEY',
        'API_TOKEN',
        'API_KEY'
    ];
    for (const key of possibleKeys) {
        const value = process.env[key];
        if (value && value.trim()) {
            return value.trim();
        }
    }
    // Zkusit session config z ENV
    const sessionConfigKeys = ['SMITHERY_SESSION_CONFIG', 'SMITHERY_CONFIG', 'MCP_SESSION_CONFIG'];
    for (const key of sessionConfigKeys) {
        const raw = process.env[key];
        if (raw) {
            try {
                const config = JSON.parse(raw);
                const token = findTokenInConfig(config);
                if (token)
                    return token;
            }
            catch (e) {
                // Ignorovat chyby parsování
            }
        }
    }
    return '';
}
function findTokenInConfig(obj) {
    if (typeof obj === 'string' && obj.length > 10) {
        return obj;
    }
    if (typeof obj === 'object' && obj !== null) {
        for (const [key, value] of Object.entries(obj)) {
            if (typeof value === 'string' && value &&
                (key.toLowerCase().includes('token') || key.toLowerCase().includes('key'))) {
                return value;
            }
            const nested = findTokenInConfig(value);
            if (nested)
                return nested;
        }
    }
    return '';
}
// Marketing Miner API volání
async function makeMarketingMinerRequest(url, params) {
    const apiToken = getApiToken();
    if (!apiToken) {
        throw new Error('Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci.');
    }
    try {
        const response = await axios_1.default.get(url, {
            params: {
                ...params,
                api_token: apiToken
            },
            timeout: 30000
        });
        return response.data;
    }
    catch (error) {
        throw new Error(`Chyba při volání Marketing Miner API: ${error}`);
    }
}
// MCP Server
const server = new index_js_1.Server({
    name: 'marketing-miner-mcp',
    version: '2.0.2',
}, {
    capabilities: {
        tools: {},
    },
});
// Initialize handler
server.setRequestHandler(types_js_1.InitializeRequestSchema, async (request) => {
    // Diagnostický log do stderr - neměl by rušit MCP komunikaci
    process.stderr.write('--- MCP: Initialize request received ---\n');
    return {
        protocolVersion: request.params.protocolVersion,
        capabilities: {
            tools: {},
        },
        serverInfo: {
            name: 'marketing-miner-mcp',
            version: '2.0.2',
        },
    };
});
// List tools handler
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'get_keyword_suggestions',
                description: 'Získá návrhy klíčových slov z Marketing Miner API',
                inputSchema: {
                    type: 'object',
                    properties: {
                        lang: {
                            type: 'string',
                            description: 'Jazyk (cs/sk/pl/hu/ro/gb/us)',
                            enum: LANGUAGES
                        },
                        keyword: {
                            type: 'string',
                            description: 'Klíčové slovo pro analýzu'
                        },
                        suggestions_type: {
                            type: 'string',
                            description: 'Typ návrhů (volitelné)',
                            enum: SUGGESTIONS_TYPES
                        },
                        with_keyword_data: {
                            type: 'boolean',
                            description: 'Zahrnout data o klíčových slovech (volitelné)',
                            default: false
                        }
                    },
                    required: ['lang', 'keyword']
                }
            },
            {
                name: 'get_search_volume_data',
                description: 'Získá data o hledanosti klíčového slova z Marketing Miner API',
                inputSchema: {
                    type: 'object',
                    properties: {
                        lang: {
                            type: 'string',
                            description: 'Jazyk (cs/sk/pl/hu/ro/gb/us)',
                            enum: LANGUAGES
                        },
                        keyword: {
                            type: 'string',
                            description: 'Klíčové slovo pro analýzu'
                        }
                    },
                    required: ['lang', 'keyword']
                }
            }
        ]
    };
});
// Call tool handler
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    if (name === 'get_keyword_suggestions') {
        const { lang, keyword, suggestions_type, with_keyword_data } = args;
        if (!LANGUAGES.includes(lang)) {
            throw new Error(`Nepodporovaný jazyk: ${lang}`);
        }
        if (suggestions_type && !SUGGESTIONS_TYPES.includes(suggestions_type)) {
            throw new Error(`Nepodporovaný typ návrhů: ${suggestions_type}`);
        }
        const url = `${API_BASE}/keywords/suggestions`;
        const params = { lang, keyword };
        if (suggestions_type) {
            params.suggestions_type = suggestions_type;
        }
        if (with_keyword_data !== undefined) {
            params.with_keyword_data = with_keyword_data.toString().toLowerCase();
        }
        try {
            const data = await makeMarketingMinerRequest(url, params);
            if (data.status === 'error') {
                return {
                    content: [{ type: 'text', text: data.message || 'Nastala neznámá chyba' }]
                };
            }
            if (data.status === 'success') {
                const keywords = data.data?.keywords || [];
                if (keywords.length === 0) {
                    return {
                        content: [{ type: 'text', text: 'Nebyla nalezena žádná data pro tento dotaz.' }]
                    };
                }
                const results = keywords.map((kw) => {
                    const info = [`Klíčové slovo: ${kw.keyword || 'N/A'}`];
                    if (kw.search_volume !== undefined) {
                        info.push(`Hledanost: ${kw.search_volume}`);
                    }
                    return info.join(' | ');
                });
                return {
                    content: [{ type: 'text', text: results.join('\\n') }]
                };
            }
            return {
                content: [{ type: 'text', text: 'Neočekávaný formát odpovědi z API' }]
            };
        }
        catch (error) {
            return {
                content: [{ type: 'text', text: error instanceof Error ? error.message : 'Nastala chyba' }]
            };
        }
    }
    if (name === 'get_search_volume_data') {
        const { lang, keyword } = args;
        if (!LANGUAGES.includes(lang)) {
            throw new Error(`Nepodporovaný jazyk: ${lang}`);
        }
        const url = `${API_BASE}/keywords/search-volume-data`;
        const params = { lang, keyword };
        try {
            const data = await makeMarketingMinerRequest(url, params);
            if (data.status === 'error') {
                return {
                    content: [{ type: 'text', text: data.message || 'Nastala neznámá chyba' }]
                };
            }
            if (data.status === 'success') {
                const results = data.data || [];
                if (results.length === 0) {
                    return {
                        content: [{ type: 'text', text: 'Nebyla nalezena žádná data pro toto klíčové slovo.' }]
                    };
                }
                const kw = results[0];
                const output = [
                    `Klíčové slovo: ${kw.keyword || 'N/A'}`,
                    `Hledanost: ${kw.search_volume || 'N/A'}`
                ];
                if (kw.cpc && kw.cpc.value) {
                    output.push(`CPC: ${kw.cpc.value} ${kw.cpc.currency_code || ''}`);
                }
                return {
                    content: [{ type: 'text', text: output.join('\\n') }]
                };
            }
            return {
                content: [{ type: 'text', text: 'Neočekávaný formát odpovědi z API' }]
            };
        }
        catch (error) {
            return {
                content: [{ type: 'text', text: error instanceof Error ? error.message : 'Nastala chyba' }]
            };
        }
    }
    throw new Error(`Neznámý tool: ${name}`);
});
// Spuštění HTTP(SSE) serveru pro MCP (kompatibilní se Smithery SHTTP/SSE)
const host = process.env.HOST || '0.0.0.0';
const port = parseInt(process.env.PORT || '8000', 10);
const mcpPath = process.env.MCP_HTTP_PATH || '/mcp';
// Uložiště aktivních SSE transportů podle sessionId
const sessionIdToTransport = new Map();
const httpServer = http_1.default.createServer(async (req, res) => {
    try {
        const urlPath = (req.url || '').split('?')[0];
        const accept = (req.headers['accept'] || '').toString();
        // Healthcheck (pokud klient nechce SSE)
        if (req.method === 'GET' && urlPath === mcpPath && !accept.includes('text/event-stream')) {
            res.writeHead(200, { 'content-type': 'text/plain' });
            res.end('OK');
            return;
        }
        // MCP SSE endpoint (GET s Accept: text/event-stream)
        if (req.method === 'GET' && urlPath === mcpPath && accept.includes('text/event-stream')) {
            // Transport vyžaduje endpoint string (pro následné POST zprávy)
            const transport = new sse_js_1.SSEServerTransport(mcpPath, res);
            await server.connect(transport);
            // Po connectu má transport přidělené sessionId, ulož ho pro POST routing
            const sid = transport.sessionId;
            if (sid) {
                sessionIdToTransport.set(sid, transport);
            }
            return;
        }
        // MCP POST zprávy (body -> JSON-RPC) na stejné cestě s parametrem sessionId
        if (req.method === 'POST' && urlPath === mcpPath) {
            const fullUrl = new url_1.URL(req.url || '', `http://${req.headers.host || 'localhost'}`);
            const sid = fullUrl.searchParams.get('sessionId') || '';
            const transport = sid ? sessionIdToTransport.get(sid) : undefined;
            if (!transport) {
                res.writeHead(400).end('Missing or invalid sessionId');
                return;
            }
            await transport.handlePostMessage(req, res);
            return;
        }
        res.writeHead(404, { 'content-type': 'text/plain' });
        res.end('Not Found');
    }
    catch (error) {
        // Kritické chyby logujeme jen do stderr
        process.stderr.write(`Kritická chyba HTTP handleru: ${error}\n`);
        try {
            res.writeHead(500, { 'content-type': 'text/plain' });
            res.end('Internal Server Error');
        }
        catch (_) {
            // ignore
        }
    }
});
httpServer.listen(port, host);
