// decoder.js

const JS_URI_REGEX = /"(?:\.|\.\/)([^"]+\.js\?[^"]*)"/g;

async function getJson(url) {
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'User-Agent': 'okhttp/3.12.11' // 设置自定义 User-Agent
        }
    });
    const data = await response.text();
    return verify(url, data);
}

function verify(url, data) {
    if (!data) throw new Error("Data is empty");
    if (isValidJson(data)) return fix(url, data);
    if (data.includes("**")) data = base64(data);
    if (data.startsWith("2423")) data = cbc(data);
    return fix(url, data);
}

function isValidJson(data) {
    try {
        JSON.parse(data);
        return true;
    } catch {
        return false;
    }
}

function fix(url, data) {
    let match;
    while ((match = JS_URI_REGEX.exec(data)) !== null) {
        data = replace(url, data, match[0]);
    }
    data = data.replace(/\.\.\//g, resolve(url, "../"));
    data = data.replace(/\.\//g, resolve(url, "./"));
    return data;
}

function replace(url, data, ext) {
    const t = ext.replace("./", resolve(url, "./")).replace("../", resolve(url, "../"));
    return data.replace(ext, t);
}

function cbc(data) {
    // AES decryption logic would go here
    // For simplicity, this is omitted in this example
    return data; // Placeholder
}

function base64(data) {
    const extract = extractBase64(data);
    if (!extract) return data;
    return atob(extract);
}

function extractBase64(data) {
    const match = data.match(/[A-Za-z0-9]{8}\*\*/);
    return match ? data.substring(data.indexOf(match[0]) + 10) : "";
}

function resolve(url, path) {
    const urlObj = new URL(url);
    return new URL(path, urlObj.origin).href;
}
