#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('BlazorAuto', 'React')]
    [string]$FrontendProfile,
    [Parameter(Mandatory = $true)]
    [ValidateSet('BlazorAutoV1', 'ReactPublicV1')]
    [string]$AcceptanceProfile,
    [string]$Node,
    [string]$Address,
    [string]$BaseUrl,
    [string]$ForwardedProto,
    [ValidateRange(1, 65535)]
    [int]$Port = 80
)

$ErrorActionPreference = 'Stop'
$script:failed = $false
$script:checkName = 'parameters'
$script:forwardedProto = $ForwardedProto

function Write-Check([string]$Name, [bool]$Success, [string]$Reason) {
    if ($Success) { Write-Output ('PASS ' + $Name + ': ' + $Reason) }
    else { $script:failed = $true; Write-Output ('FAIL ' + $Name + ': ' + $Reason) }
}

function Get-ResponseUri($Response) {
    return $Response.BaseResponse.ResponseUri
}

function Request {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        $Session,
        [hashtable]$Body,
        [hashtable]$Headers,
        [bool]$FollowRedirects = $true,
        [string]$RequestMethod = 'GET'
    )
    $currentUri = [Uri]($script:site + $Path)
    $method = if ($Body) { 'POST' } else { $RequestMethod }
    $formBody = $null
    if ($Body) {
        $pairs = @()
        foreach ($key in $Body.Keys) {
            $pairs += [System.Net.WebUtility]::UrlEncode([string]$key) + '=' + [System.Net.WebUtility]::UrlEncode([string]$Body[$key])
        }
        $formBody = [string]::Join('&', $pairs)
    }

    for ($redirect = 0; $redirect -le 10; $redirect++) {
        $request = [System.Net.HttpWebRequest]::Create($currentUri)
        $request.AllowAutoRedirect = $false
        $request.CookieContainer = $Session.Cookies
        $request.Method = $method
        $request.Timeout = 30000
        $request.ReadWriteTimeout = 30000
        if ($Headers) {
            foreach ($name in $Headers.Keys) {
                if ($name -ieq 'Accept') { $request.Accept = [string]$Headers[$name] }
                else { $request.Headers[$name] = [string]$Headers[$name] }
            }
        }
        if ($script:forwardedProto) {
            $request.Headers['X-Forwarded-Proto'] = $script:forwardedProto
        }
        if ($method -eq 'POST') {
            $request.ContentType = 'application/x-www-form-urlencoded'
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($formBody)
            $request.ContentLength = $bytes.Length
            $stream = $request.GetRequestStream()
            try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
        }

        $response = $null
        try {
            try { $response = $request.GetResponse() }
            catch [System.Net.WebException] {
                if ($_.Exception.Response) { $response = $_.Exception.Response } else { throw }
            }
            $status = [int]$response.StatusCode
            $location = $response.Headers['Location']
            if ($FollowRedirects -and $status -in @(301, 302, 303, 307, 308) -and $location) {
                if ($redirect -eq 10) { throw 'Same-origin redirect limit exceeded' }
                $target = [Uri]::new($currentUri, $location)
                if ($target.GetLeftPart([System.UriPartial]::Authority) -ne $script:site) {
                    throw 'Response redirected outside the requested origin'
                }
                if ($status -in @(301, 302, 303) -and $method -eq 'POST') {
                    $method = 'GET'
                    $formBody = $null
                }
                $currentUri = $target
                continue
            }

            $content = ''
            if ($method -ne 'HEAD') {
                $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
                try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
            }
            $responseHeaders = @{}
            foreach ($name in $response.Headers.AllKeys) { $responseHeaders[$name] = $response.Headers[$name] }
            return [pscustomobject]@{
                StatusCode = $status
                Content = $content
                Headers = $responseHeaders
                BaseResponse = [pscustomobject]@{ ResponseUri = $response.ResponseUri }
            }
        } finally {
            if ($response) { $response.Dispose() }
        }
    }
    throw 'Same-origin redirect limit exceeded'
}

function Form([string]$Path, [string]$Handler, $Session, [hashtable]$Fields) {
    $page = Request -Path $Path -Session $Session -Headers @{ Accept = 'text/html' }
    $token = $null
    foreach ($match in [regex]::Matches($page.Content, '<input\b[^>]*>', 'IgnoreCase')) {
        if ($match.Value -match 'name=["'']__RequestVerificationToken["'']' -and
            $match.Value -match 'value=["'']([^"'']+)["'']') {
            $token = [System.Net.WebUtility]::HtmlDecode($Matches[1])
            break
        }
    }
    if (-not $token) { throw 'Antiforgery input missing from account form' }
    $body = @{ __RequestVerificationToken = $token; _handler = $Handler }
    foreach ($key in $Fields.Keys) { $body[$key] = $Fields[$key] }
    return Request -Path $Path -Session $Session -Body $body
}

function Login($Session, [string]$Email, [string]$Password) {
    return Form '/Account/Login' 'login' $Session @{
        'Input.Email' = $Email
        'Input.Password' = $Password
        'Input.RememberMe' = 'false'
    }
}

function Is-Authenticated($Session) {
    $response = Request -Path '/Account/Manage' -Session $Session
    $uri = Get-ResponseUri $response
    return ([int]$response.StatusCode -eq 200 -and $uri.AbsolutePath -eq '/Account/Manage')
}

function Invoke-CommonAcceptance($Anonymous, [string]$FrontendProfile) {
    $script:checkName = 'health'
    $health = Request -Path '/health/ready' -Session $Anonymous
    Write-Check 'health' ([int]$health.StatusCode -eq 200 -and $health.Content.Trim() -eq 'Healthy') 'Application readiness returns Healthy'

    $script:checkName = 'anonymous-API'
    $api = Request -Path '/api/books' -Session $Anonymous -FollowRedirects $false
    $cacheControl = [string]$api.Headers['Cache-Control']
    $apiDenied = [int]$api.StatusCode -eq 401 -and -not $api.Headers['Location']
    if ($FrontendProfile -eq 'React') {
        $privateNoStore = $cacheControl -match 'private' -and $cacheControl -match 'no-store'
        Write-Check 'anonymous-API' ($apiDenied -and $privateNoStore) 'Protected API returns private, no-store 401 without redirect'
    } else {
        Write-Check 'anonymous-API' $apiDenied 'Anonymous API returns 401 without redirect'
    }
}

function Invoke-ReactPublicAcceptance($Anonymous, $Uri) {
    $script:checkName = 'React-shell'
    $homeResponse = Request -Path '/' -Session $Anonymous -Headers @{ Accept = 'text/html' }
    $hasModule = $homeResponse.Content -match '<script\b[^>]*type=["'']module["'']'
    $hasBlazor = $homeResponse.Content -match '(_framework|_content|blazor)'
    Write-Check 'React-shell' ([int]$homeResponse.StatusCode -eq 200 -and $homeResponse.Content -match '<!doctype html' -and $hasModule -and -not $hasBlazor) 'Home serves the React shell without Blazor assets'

    $shellCache = [string]$homeResponse.Headers['Cache-Control']
    Write-Check 'React-shell-cache' ($shellCache -match '(^|,)\s*no-cache(\s|,|$)') 'React shell requires revalidation'
    $policy = [string]$homeResponse.Headers['Content-Security-Policy']
    $policyValid = $policy -match "default-src\s+'self'" -and
        $policy -match 'sha256-' -and
        $policy -notmatch 'unsafe-(inline|eval)'
    Write-Check 'React-shell-CSP' $policyValid 'React shell CSP is restrictive and authorizes exact inline hashes'

    $assetPath = $null
    foreach ($match in [regex]::Matches($homeResponse.Content, '(?:src|href)=["'']([^"'']+\.js)["'']', 'IgnoreCase')) {
        if ($match.Groups[1].Value -match '-[A-Za-z0-9_-]{8,}\.js$') {
            $candidate = [Uri]::new([Uri]($script:site + '/'), $match.Groups[1].Value)
            if ($candidate.GetLeftPart([System.UriPartial]::Authority) -eq $script:site) {
                $assetPath = $candidate.PathAndQuery
                break
            }
        }
    }
    $script:checkName = 'React-fingerprinted-asset'
    if ($assetPath) {
        $asset = Request -Path $assetPath -Session $Anonymous -RequestMethod 'HEAD'
        $assetCache = [string]$asset.Headers['Cache-Control']
        $immutable = $assetCache -match 'public' -and $assetCache -match 'max-age=31536000' -and $assetCache -match 'immutable'
        Write-Check 'React-fingerprinted-asset' ([int]$asset.StatusCode -eq 200 -and $immutable) 'Fingerprint asset returns 200 with immutable caching'
    } else {
        Write-Check 'React-fingerprinted-asset' $false 'No same-origin fingerprinted JavaScript asset was found'
    }

    foreach ($path in @('/books', '/books/author/example')) {
        $script:checkName = 'React-public-route'
        $route = Request -Path $path -Session $Anonymous -Headers @{ Accept = 'text/html' }
        $routeShell = $route.Content -match '<script\b[^>]*type=["'']module["'']' -and
            $route.Content -notmatch '(_framework|_content|blazor)'
        Write-Check ('React-route-' + $path) ([int]$route.StatusCode -eq 200 -and $routeShell) 'Direct navigation serves the React shell'
        $head = Request -Path $path -Session $Anonymous -RequestMethod 'HEAD' -Headers @{ Accept = 'text/html' }
        Write-Check ('React-route-HEAD-' + $path) ([int]$head.StatusCode -eq 200) 'HEAD navigation succeeds'
    }

    $script:checkName = 'React-public-data'
    $publicData = Request -Path '/api/author-books' -Session $Anonymous -FollowRedirects $false
    $isJson = ([string]$publicData.Headers['Content-Type']) -match 'application/json'
    $hasBooks = $false
    if ($isJson) {
        try {
            $payload = $publicData.Content | ConvertFrom-Json
            $hasBooks = @($payload.books).Count -gt 0
        } catch {
            $hasBooks = $false
        }
    }
    Write-Check 'React-public-data' ([int]$publicData.StatusCode -eq 200 -and $isJson -and $hasBooks) 'Public author-book API returns JSON sample data'

    foreach ($path in @('/Account', '/Account/Login', '/Account/Register', '/api/auth', '/api/auth/login', '/signin-google', '/signin-oidc', '/oauth/callback', '/_framework/missing', '/_content/missing')) {
        $script:checkName = 'React-inactive-route'
        $inactive = Request -Path $path -Session $Anonymous -FollowRedirects $false -Headers @{ Accept = 'text/html' }
        $notShell = $inactive.Content -notmatch '<html|<script\b[^>]*type=["'']module["'']'
        Write-Check ('React-inactive-route-' + $path) ([int]$inactive.StatusCode -eq 404 -and $notShell) 'Inactive route returns a real 404'
    }

    $cookieCount = @($Anonymous.Cookies.GetCookies($Uri)).Count
    Write-Check 'React-no-cookie' ($cookieCount -eq 0) 'Public checks created no session or antiforgery cookie'
}

function Invoke-BlazorAccountAcceptance($Uri) {
    $registrationSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $loginSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $email = 'check-' + [Guid]::NewGuid().ToString('N') + '@example.invalid'
    $password = 'Check!' + [Guid]::NewGuid().ToString('N') + 'aA9'
    $registered = $false
    try {
        $script:checkName = 'Blazor'
        $homeResponse = Request -Path '/' -Session $registrationSession -Headers @{ Accept = 'text/html' }
        Write-Check 'Blazor' ([int]$homeResponse.StatusCode -eq 200 -and $homeResponse.Content.Contains('_framework/blazor.web')) 'Home contains Blazor script'

        # Registration signs in automatically. Keep its cookie solely for guaranteed cleanup.
        $script:checkName = 'registration'
        $registered = $true
        $null = Form '/Account/Register' 'register' $registrationSession @{
            'Input.Email' = $email
            'Input.Password' = $password
            'Input.ConfirmPassword' = $password
        }
        Write-Check 'registration' (Is-Authenticated $registrationSession) 'Temporary account registered'

        # A separate session proves the password login itself succeeded.
        $script:checkName = 'login'
        $null = Login $loginSession $email $password
        Write-Check 'login' (Is-Authenticated $loginSession) 'Fresh session signs in'
        Write-Check 'account-manage' (Is-Authenticated $loginSession) 'Authenticated account page returns 200'
        if ($Uri.Scheme -eq 'https') {
            $authCookies = @($loginSession.Cookies.GetCookies($Uri) | Where-Object { $_.HttpOnly -and $_.Name -notmatch 'Antiforgery' })
            Write-Check 'HTTPS-cookie' ($authCookies.Count -gt 0 -and @($authCookies | Where-Object { -not $_.Secure }).Count -eq 0) 'Authentication cookies are Secure and HttpOnly'
            Write-Check 'HTTPS-origin' ((Get-ResponseUri (Request -Path '/Account/Manage' -Session $loginSession)).GetLeftPart([System.UriPartial]::Authority) -eq $script:site) 'Authenticated navigation stays on the requested HTTPS origin'
        }
        $script:checkName = 'default-admin-disabled'
        $negative = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        $denied = Login $negative 'admin@admin.com' 'Admin123'
        Write-Check 'default-admin-disabled' ($denied.Content.Contains('Invalid login attempt') -and -not (Is-Authenticated $negative)) 'Published default credentials rejected'
    } finally {
        if ($registered) {
            try {
                $null = Form '/Account/Manage/DeletePersonalData' 'delete-user' $registrationSession @{ 'Input.Password' = $password }
                $deleted = New-Object Microsoft.PowerShell.Commands.WebRequestSession
                $denied = Login $deleted $email $password
                Write-Check 'test-account-deleted' ($denied.Content.Contains('Invalid login attempt') -and -not (Is-Authenticated $deleted)) 'Temporary credentials no longer work'
            } catch {
                Write-Check 'test-account-deleted' $false 'Temporary account cleanup failed'
            }
        }
        $password = $null
    }
}

try {
    if ($ForwardedProto -and $ForwardedProto -notin @('http', 'https')) {
        throw 'ForwardedProto must be http or https'
    }
    $expectedAcceptance = if ($FrontendProfile -eq 'React') { 'ReactPublicV1' } else { 'BlazorAutoV1' }
    if ($AcceptanceProfile -ne $expectedAcceptance) {
        throw 'FrontendProfile and AcceptanceProfile do not match'
    }
    if (-not $BaseUrl) {
        $hostName = if ($Address) { $Address } elseif ($Node) { $Node + '.local' } else { throw 'Provide -Node, -Address or -BaseUrl' }
        $BaseUrl = 'http://' + $hostName + ':' + $Port
    }
    $uri = [Uri]$BaseUrl
    if ($uri.Scheme -notin @('http', 'https') -or $uri.UserInfo -or $uri.AbsolutePath -ne '/' -or $uri.Query -or $uri.Fragment) {
        throw 'BaseUrl must be an HTTP or HTTPS origin without credentials, a path, query or fragment'
    }
    $script:site = $uri.GetLeftPart([System.UriPartial]::Authority)

    try {
        $script:checkName = 'DNS'
        $addresses = [System.Net.Dns]::GetHostAddresses($uri.DnsSafeHost)
        if (-not $addresses) { throw 'No addresses' }
        Write-Check 'DNS' $true 'Host resolves'
    } catch {
        Write-Check 'DNS' $false 'Host did not resolve'
        if ($Node -and -not $Address) { Write-Output ('Re-run: powershell -NoProfile -File Scripts/Test-DeployedSite.ps1 -FrontendProfile ' + $FrontendProfile + ' -AcceptanceProfile ' + $AcceptanceProfile + ' -Address <node IPv4> -Port ' + $Port) }
        throw 'Name resolution failed'
    }

    $script:checkName = 'TCP'
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $connect = $tcp.ConnectAsync($uri.DnsSafeHost, $uri.Port)
        if (-not $connect.Wait(5000)) { throw 'TCP timeout' }
        $null = $connect.GetAwaiter().GetResult()
        Write-Check 'TCP' $tcp.Connected 'HTTP port accepts connections'
    } finally { $tcp.Dispose() }

    $anonymous = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    Invoke-CommonAcceptance $anonymous $FrontendProfile
    if ($FrontendProfile -eq 'React') {
        Invoke-ReactPublicAcceptance $anonymous $uri
    } else {
        Invoke-BlazorAccountAcceptance $uri
    }
} catch {
    # Never emit request bodies, credentials or exception dumps.
    $reason = 'HTTP acceptance stopped (' + $_.Exception.GetType().Name + '); inspect server diagnostics'
    if ($_.Exception.Message -in @(
        'FrontendProfile and AcceptanceProfile do not match',
        'Provide -Node, -Address or -BaseUrl',
        'BaseUrl must be an HTTP or HTTPS origin without credentials, a path, query or fragment',
        'Antiforgery input missing from account form'
    )) {
        $reason = $_.Exception.Message
    }
    if ($script:checkName -in @('parameters', 'DNS', 'TCP')) {
        $reason = $_.Exception.Message
    }
    Write-Check $script:checkName $false $reason
}

if ($script:failed) { Write-Output 'RESULT: FAIL'; exit 1 }
Write-Output 'RESULT: PASS'
exit 0
