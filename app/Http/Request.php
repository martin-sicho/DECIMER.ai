<?php

namespace App\Http;

use Illuminate\Http\Request as BaseRequest;

class Request extends BaseRequest
{
    /**
     * Use the URL prefix passed by the web server (APP_URL_PREFIX, e.g. "/decimer")
     * as the base URL, so routing ignores it and generated URLs include it.
     *
     * @return string
     */
    protected function prepareBaseUrl()
    {
        $prefix = rtrim((string) $this->server->get('APP_URL_PREFIX'), '/');
        $path = strtok((string) $this->getRequestUri(), '?');

        if ($prefix !== '' && ($path === $prefix || str_starts_with($path, $prefix . '/'))) {
            return $prefix;
        }

        return parent::prepareBaseUrl();
    }
}
