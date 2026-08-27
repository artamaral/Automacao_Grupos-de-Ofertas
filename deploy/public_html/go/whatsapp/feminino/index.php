<?php

declare(strict_types=1);

const WHATSAPP_INVITE_HOST = 'chat.whatsapp.com';
const WHATSAPP_INVITE_PATH_PATTERN = '~^/[A-Za-z0-9]{20,24}/?$~D';

function renderUnavailablePage(): never
{
    http_response_code(503);
    header('Content-Type: text/html; charset=UTF-8');
    header('Cache-Control: no-store, max-age=0');
    header('X-Robots-Tag: noindex, nofollow');

    $errorPage = dirname(__DIR__, 3) . '/error/whatsapp-indisponivel.html';
    if (is_file($errorPage) && is_readable($errorPage)) {
        readfile($errorPage);
    } else {
        echo '<!doctype html><html lang="pt-BR"><meta charset="utf-8">';
        echo '<title>Acesso temporariamente indisponível</title>';
        echo '<p>O acesso ao grupo está temporariamente indisponível. ';
        echo 'Tente novamente em alguns minutos.</p>';
    }

    exit;
}

function isAcceptedWhatsAppInvite(mixed $candidate): bool
{
    if (!is_string($candidate) || trim($candidate) === '') {
        return false;
    }

    $url = trim($candidate);
    if (filter_var($url, FILTER_VALIDATE_URL) === false) {
        return false;
    }

    $parts = parse_url($url);
    if (!is_array($parts)) {
        return false;
    }

    $scheme = strtolower((string) ($parts['scheme'] ?? ''));
    $host = strtolower((string) ($parts['host'] ?? ''));
    $path = (string) ($parts['path'] ?? '');

    return $scheme === 'https'
        && $host === WHATSAPP_INVITE_HOST
        && !isset($parts['user'], $parts['pass'], $parts['port'], $parts['query'], $parts['fragment'])
        && preg_match(WHATSAPP_INVITE_PATH_PATTERN, $path) === 1;
}

$configFile = dirname(__DIR__, 3) . '/_config/whatsapp.php';
if (!is_file($configFile) || !is_readable($configFile)) {
    renderUnavailablePage();
}

$config = require $configFile;
$destination = is_array($config) ? ($config['WHATSAPP_GROUP_URL_FEMININO'] ?? null) : null;

if (!isAcceptedWhatsAppInvite($destination)) {
    renderUnavailablePage();
}

header('Cache-Control: no-store, max-age=0');
header('Location: ' . trim($destination), true, 302);
exit;
