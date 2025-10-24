#!/usr/bin/env node
/**
 * Script de teste para verificar se o servidor PaddleOCR está funcionando corretamente
 * e se o CORS está configurado adequadamente.
 */

const https = require('https');
const http = require('http');

function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const client = isHttps ? https : http;
        
        const requestOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port || (isHttps ? 443 : 80),
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: options.headers || {},
            timeout: 10000
        };

        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    headers: res.headers,
                    data: data
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        if (options.body) {
            req.write(options.body);
        }

        req.end();
    });
}

async function testHealthEndpoint() {
    console.log('🔍 Testando endpoint de health...');
    console.log('-'.repeat(40));
    
    try {
        const url = 'https://ocr.essencialab.app/health';
        console.log(`URL: ${url}`);
        
        const response = await makeRequest(url);
        console.log(`Status Code: ${response.statusCode}`);
        console.log(`Headers:`, JSON.stringify(response.headers, null, 2));
        
        if (response.statusCode === 200) {
            const data = JSON.parse(response.data);
            console.log(`Response:`, JSON.stringify(data, null, 2));
            console.log('✅ Health endpoint OK');
            return true;
        } else {
            console.log(`❌ Erro: ${response.data}`);
            return false;
        }
    } catch (error) {
        console.log(`❌ Erro ao testar health endpoint: ${error.message}`);
        return false;
    }
}

async function testCORSPreflight() {
    console.log('\n🔍 Testando CORS preflight...');
    console.log('-'.repeat(40));
    
    try {
        const url = 'https://ocr.essencialab.app/ocr';
        console.log(`URL: ${url}`);
        
        const headers = {
            'Origin': 'https://essencialab.app',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type,Authorization,X-Requested-With'
        };
        
        const response = await makeRequest(url, { method: 'OPTIONS', headers });
        console.log(`Status Code: ${response.statusCode}`);
        console.log(`Headers:`, JSON.stringify(response.headers, null, 2));
        
        const corsHeaders = {
            'Access-Control-Allow-Origin': response.headers['access-control-allow-origin'],
            'Access-Control-Allow-Methods': response.headers['access-control-allow-methods'],
            'Access-Control-Allow-Headers': response.headers['access-control-allow-headers'],
        };
        
        console.log(`CORS Headers:`, JSON.stringify(corsHeaders, null, 2));
        
        if (response.statusCode === 200 && corsHeaders['Access-Control-Allow-Origin'] === '*') {
            console.log('✅ CORS preflight OK');
            return true;
        } else {
            console.log('❌ CORS preflight falhou');
            return false;
        }
    } catch (error) {
        console.log(`❌ Erro ao testar CORS preflight: ${error.message}`);
        return false;
    }
}

async function testInfoEndpoint() {
    console.log('\n🔍 Testando endpoint de info...');
    console.log('-'.repeat(40));
    
    try {
        const url = 'https://ocr.essencialab.app/info';
        console.log(`URL: ${url}`);
        
        const response = await makeRequest(url);
        console.log(`Status Code: ${response.statusCode}`);
        
        if (response.statusCode === 200) {
            const data = JSON.parse(response.data);
            console.log(`API Info:`, JSON.stringify(data, null, 2));
            console.log('✅ Info endpoint OK');
            return true;
        } else {
            console.log(`❌ Erro: ${response.data}`);
            return false;
        }
    } catch (error) {
        console.log(`❌ Erro ao testar info endpoint: ${error.message}`);
        return false;
    }
}

async function main() {
    console.log('🧪 Iniciando testes do servidor PaddleOCR...');
    console.log('='.repeat(60));
    
    const tests = [
        { name: 'Health Check', func: testHealthEndpoint },
        { name: 'CORS Preflight', func: testCORSPreflight },
        { name: 'API Info', func: testInfoEndpoint },
    ];
    
    const results = [];
    
    for (const test of tests) {
        console.log(`\n🔍 Executando: ${test.name}`);
        const result = await test.func();
        results.push({ name: test.name, passed: result });
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 RESUMO DOS TESTES:');
    console.log('='.repeat(60));
    
    let allPassed = true;
    for (const result of results) {
        const status = result.passed ? '✅ PASSOU' : '❌ FALHOU';
        console.log(`${result.name}: ${status}`);
        if (!result.passed) {
            allPassed = false;
        }
    }
    
    console.log('='.repeat(60));
    if (allPassed) {
        console.log('🎉 TODOS OS TESTES PASSARAM! O servidor está funcionando corretamente.');
        process.exit(0);
    } else {
        console.log('⚠️  ALGUNS TESTES FALHARAM. Verifique os logs acima.');
        process.exit(1);
    }
}

if (require.main === module) {
    main().catch(console.error);
}
