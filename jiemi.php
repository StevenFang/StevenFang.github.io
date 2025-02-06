<?php

class Decoder {
    private static $JS_URI_PATTERN = '/"(?:\.|\.\/)([^\/]+\.js\?[^"]*)"/';

    public static function getJson($url) {
        $response = self::httpGet($url);
        return self::verify($url, $response);
    }

    private static function httpGet($url) {
        $options = [
            "http" => [
                "header" => "User-Agent: PHP\r\n",
                "method" => "GET"
            ]
        ];
        $context = stream_context_create($options);
        return file_get_contents($url, false, $context);
    }

    private static function verify($url, $data) {
        if (empty($data)) {
            throw new Exception("Empty data");
        }
        if (self::isValidJson($data)) {
            return self::fix($url, $data);
        }
        if (strpos($data, '**') !== false) {
            $data = self::base64($data);
        }
        if (strpos($data, '2423') === 0) {
            $data = self::cbc($data);
        }
        return self::fix($url, $data);
    }

    private static function isValidJson($data) {
        json_decode($data);
        return (json_last_error() === JSON_ERROR_NONE);
    }

    private static function fix($url, $data) {
        preg_match_all(self::$JS_URI_PATTERN, $data, $matches);
        foreach ($matches[0] as $match) {
            $data = self::replace($url, $data, $match);
        }
        $data = str_replace('../', self::resolveUrl($url, '../'), $data);
        $data = str_replace('./', self::resolveUrl($url, './'), $data);
        $data = str_replace('__JS1__', './', $data);
        $data = str_replace('__JS2__', '../', $data);
        return $data;
    }

    private static function replace($url, $data, $ext) {
        $t = str_replace('./', self::resolveUrl($url, './'), $ext);
        $t = str_replace('../', self::resolveUrl($url, '../'), $t);
        $t = str_replace('./', '__JS1__', $t);
        $t = str_replace('../', '__JS2__', $t);
        return str_replace($ext, $t, $data);
    }

    private static function cbc($data) {
        $decode = hex2bin($data);
        $key = self::padEnd(substr($decode, strpos($decode, '$#') + 2, strpos($decode, '#$') - strpos($decode, '$#') - 2));
        $iv = self::padEnd(substr($decode, -13));
        $data = substr($data, strpos($data, '2324') + 4, -26);
        $data = hex2bin($data);
        return openssl_decrypt($data, 'AES-128-CBC', $key, OPENSSL_RAW_DATA, $iv);
    }

    private static function base64($data) {
        $extract = self::extract($data);
        if (empty($extract)) {
            return $data;
        }
        return base64_decode($extract);
    }

    private static function extract($data) {
        preg_match('/([A-Za-z0-9]{8}\*\*)/', $data, $matches);
        return isset($matches[0]) ? substr($data, strpos($data, $matches[0]) + 10) : '';
    }

    private static function padEnd($key) {
        return str_pad($key, 16, '0');
    }

    private static function resolveUrl($base, $relative) {
        return rtrim(dirname($base), '/') . '/' . ltrim($relative, '/');
    }
}

// 从用户输入获取 URL
echo "请输入 URL: ";
$url = trim(fgets(STDIN));

try {
    $json = Decoder::getJson($url);
    echo $json;
} catch (Exception $e) {
    echo "Error: " . $e->getMessage();
}
