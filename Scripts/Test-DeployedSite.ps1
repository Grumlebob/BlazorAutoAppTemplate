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
    $arguments = @{
        Uri = $script:site + $Path
        WebSession = $Session
        UseBasicParsing = $true
        TimeoutSec = 30
        MaximumRedirection = 10
    }
    if ($Body) {
        $arguments.Method = 'POST'
        $arguments.Body = $Body
        $arguments.ContentType = 'application/x-www-form-urlencoded'
    }
    return Invoke-WebRequest @arguments
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
    if ($uri.Scheme -ne 'http' -or $uri.UserInfo -or $uri.AbsolutePath -ne '/') {
        throw 'BaseUrl must be a plain HTTP origin without credentials or a path'
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
    Write-Check 'health' ([int]$health.StatusCode -eq 200) 'Readiness returns 200'
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
