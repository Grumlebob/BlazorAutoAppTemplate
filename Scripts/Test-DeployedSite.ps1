#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Node,
    [string]$Address,
    [string]$BaseUrl,
    [ValidateRange(1, 65535)][int]$Port = 80
)
$ErrorActionPreference = 'Stop'
$failed = $false
$registered = $false
$checkName = 'parameters'
$registrationSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$email = 'check-' + [Guid]::NewGuid().ToString('N') + '@example.invalid'
$password = 'Check!' + [Guid]::NewGuid().ToString('N') + 'aA9'

function Write-Check([string]$Name, [bool]$Success, [string]$Reason) {
    if ($Success) { Write-Output "PASS ${Name}: $Reason" }
    else { $script:failed = $true; Write-Output "FAIL ${Name}: $Reason" }
}

function Get-ResponseUri($Response) {
    if ($Response.BaseResponse.ResponseUri) { return $Response.BaseResponse.ResponseUri }
    return $Response.BaseResponse.RequestMessage.RequestUri
}

function Request([string]$Path, $Session, [hashtable]$Body) {
    $currentUri = [Uri]($script:site + $Path)
    $method = 'GET'
    $formBody = $null
    if ($Body) {
        $method = 'POST'
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
            if ($status -in @(301, 302, 303, 307, 308) -and $location) {
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

            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
            $headers = @{}
            foreach ($name in $response.Headers.AllKeys) { $headers[$name] = $response.Headers[$name] }
            return [pscustomobject]@{
                StatusCode = $status
                Content = $content
                Headers = $headers
                BaseResponse = [pscustomobject]@{ ResponseUri = $response.ResponseUri }
            }
        } finally {
            if ($response) { $response.Dispose() }
        }
    }
    throw 'Same-origin redirect limit exceeded'
}

function Form([string]$Path, [string]$Handler, $Session, [hashtable]$Fields) {
    $page = Request $Path $Session
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
    return Request $Path $Session $body
}

function Login($Session, [string]$Email, [string]$Password) {
    return Form '/Account/Login' 'login' $Session @{
        'Input.Email' = $Email
        'Input.Password' = $Password
        'Input.RememberMe' = 'false'
    }
}

function Is-Authenticated($Session) {
    $response = Request '/Account/Manage' $Session
    $uri = Get-ResponseUri $response
    return ([int]$response.StatusCode -eq 200 -and $uri.AbsolutePath -eq '/Account/Manage')
}

try {
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
        $checkName = 'DNS'
        $addresses = [System.Net.Dns]::GetHostAddresses($uri.DnsSafeHost)
        if (-not $addresses) { throw 'No addresses' }
        Write-Check 'DNS' $true 'Host resolves'
    } catch {
        Write-Check 'DNS' $false 'Host did not resolve'
        if ($Node -and -not $Address) { Write-Output "Re-run: powershell -NoProfile -File Scripts/Test-DeployedSite.ps1 -Address <node IPv4> -Port $Port" }
        throw 'Name resolution failed'
    }
    $checkName = 'TCP'
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $connect = $tcp.ConnectAsync($uri.DnsSafeHost, $uri.Port)
        if (-not $connect.Wait(5000)) { throw 'TCP timeout' }
        $connect.GetAwaiter().GetResult()
        Write-Check 'TCP' $tcp.Connected 'HTTP port accepts connections'
    } finally { $tcp.Dispose() }
    $anonymous = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $checkName = 'health'
    $health = Request '/health/ready' $anonymous
    Write-Check 'health' ([int]$health.StatusCode -eq 200 -and $health.Content.Trim() -eq 'Healthy') 'Application readiness returns Healthy'
    $checkName = 'Blazor'
    $homeResponse = Request '/' $anonymous
    Write-Check 'Blazor' ([int]$homeResponse.StatusCode -eq 200 -and $homeResponse.Content.Contains('_framework/blazor.web')) 'Home contains Blazor script'
    $apiStatus = 0
    $apiRedirect = $false
    try {
        $api = Invoke-WebRequest -Uri ($script:site + '/api/books') -WebSession $anonymous -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0
        $apiStatus = [int]$api.StatusCode
        $apiRedirect = [bool]$api.Headers['Location']
    } catch {
        if ($_.Exception.Response) {
            $apiStatus = [int]$_.Exception.Response.StatusCode
            $headers = $_.Exception.Response.Headers
            if ($headers.Location) { $apiRedirect = $true }
        }
    }
    Write-Check 'anonymous-API' ($apiStatus -eq 401 -and -not $apiRedirect) 'Anonymous API returns 401 without redirect'
    # Registration signs in automatically. Keep its cookie solely for guaranteed cleanup.
    $checkName = 'registration'
    $registered = $true
    $null = Form '/Account/Register' 'register' $registrationSession @{
        'Input.Email' = $email
        'Input.Password' = $password
        'Input.ConfirmPassword' = $password
    }
    Write-Check 'registration' (Is-Authenticated $registrationSession) 'Temporary account registered'
    # A separate session proves the password login itself succeeded.
    $checkName = 'login'
    $null = Login $loginSession $email $password
    Write-Check 'login' (Is-Authenticated $loginSession) 'Fresh session signs in'
    Write-Check 'account-manage' (Is-Authenticated $loginSession) 'Authenticated account page returns 200'
    if ($uri.Scheme -eq 'https') {
        $authCookies = @($loginSession.Cookies.GetCookies($uri) | Where-Object { $_.HttpOnly -and $_.Name -notmatch 'Antiforgery' })
        Write-Check 'HTTPS-cookie' ($authCookies.Count -gt 0 -and @($authCookies | Where-Object { -not $_.Secure }).Count -eq 0) 'Authentication cookies are Secure and HttpOnly'
        Write-Check 'HTTPS-origin' ((Get-ResponseUri (Request '/Account/Manage' $loginSession)).GetLeftPart([System.UriPartial]::Authority) -eq $script:site) 'Authenticated navigation stays on the requested HTTPS origin'
    }
    $checkName = 'default-admin-disabled'
    $negative = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $denied = Login $negative 'admin@admin.com' 'Admin123'
    Write-Check 'default-admin-disabled' ($denied.Content.Contains('Invalid login attempt') -and -not (Is-Authenticated $negative)) 'Published default credentials rejected'
} catch {
    # Account requests carry credentials; never emit request bodies or exception dumps.
    $reason = 'HTTP acceptance stopped (' + $_.Exception.GetType().Name + '); inspect server diagnostics'
    if ($_.Exception.Message -eq 'Antiforgery input missing from account form') {
        $reason = $_.Exception.Message
    }
    if ($checkName -in @('parameters', 'DNS', 'TCP', 'health', 'Blazor')) {
        $reason = $_.Exception.Message
    }
    Write-Check $checkName $false $reason
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
if ($failed) { Write-Output 'RESULT: FAIL'; exit 1 }
Write-Output 'RESULT: PASS'
exit 0
