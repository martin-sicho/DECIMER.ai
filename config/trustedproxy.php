<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Trusted Proxies
    |--------------------------------------------------------------------------
    |
    | Comma-separated IP addresses or CIDR ranges of reverse proxies whose
    | X-Forwarded-* headers are trusted (e.g. a TLS-terminating proxy, so that
    | generated URLs use https), or "*" to trust the calling proxy. Leave empty
    | to trust no proxies.
    |
    */

    'proxies' => env('TRUSTED_PROXIES') ?: null,

];
