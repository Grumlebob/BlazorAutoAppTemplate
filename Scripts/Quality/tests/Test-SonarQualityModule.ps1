[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\SonarQuality.psm1') -Force -DisableNameChecking

$passed = 0
function Assert-Equal {
    param([object]$Actual, [object]$Expected, [string]$Name)
    if ($Actual -cne $Expected) { throw "$Name expected '$Expected', got '$Actual'." }
    $script:passed++
}
function Assert-Throws {
    param([scriptblock]$Action, [string]$Name)
    try { & $Action; throw "$Name did not fail." }
    catch { if ($_.Exception.Message -eq "$Name did not fail.") { throw } }
    $script:passed++
}

$secret = 'module-test-token-sentinel'
$arguments = @(ConvertTo-QualityDisplayArguments -Arguments @('/k:project', "/d:sonar.token=$secret", 'Authorization: Bearer value123'))
Assert-Equal $arguments[0] '/k:project' 'safe scanner argument'
if (($arguments -join ' ') -match [regex]::Escape($secret) -or ($arguments -join ' ') -match 'value123') { throw 'Argument display leaked a credential.' }
$redacted = Protect-QualityText -Text "before $secret after" -Secrets @($secret)
if ($redacted.Contains($secret) -or -not $redacted.Contains('[REDACTED]')) { throw 'Protect-QualityText did not redact the supplied secret.' }
$passed++

Assert-Equal (ConvertTo-RepositoryIdentity 'https://user:password@example.com/Owner/Repo.git') 'example.com/Owner/Repo' 'origin normalization'
Assert-Throws { ConvertTo-RepositoryIdentity 'file:///tmp/repo' } 'unsupported origin scheme'
Assert-Equal (New-QualityAuthHeader -Token 'token-value').Authorization 'Bearer token-value' 'bearer authentication'
Assert-Throws { New-QualityAuthHeader -User admin } 'incomplete basic authentication'
Assert-Equal (Get-QualityTokenProjectKey -Token ([pscustomobject]@{ projectKey = 'legacy-project-key' })) 'legacy-project-key' 'legacy token project key'
Assert-Equal (Get-QualityTokenProjectKey -Token ([pscustomobject]@{ project = [pscustomobject]@{ key = 'current-project-key'; name = 'Current project' } })) 'current-project-key' 'current token project key'
Assert-Equal (Get-QualityTokenProjectKey -Token ([pscustomobject]@{ project = $null })) $null 'missing token project key'

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "quality-module-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    $safePath = Join-Path $tempRoot 'reports/summary.json'
    Assert-Equal (Test-QualityPathWithinRoot -Path $safePath -Root $tempRoot) $true 'path containment'
    Assert-Equal (Test-QualityPathWithinRoot -Path (Join-Path $tempRoot '../outside.json') -Root $tempRoot) $false 'path escape rejection'
    Assert-Throws { Assert-QualitySafeChildPath -Path (Join-Path $tempRoot 'NUL.txt') -Root $tempRoot } 'reserved path rejection'
    Assert-Throws {
        Invoke-QualityApi -BaseUrl 'https://sonar.example.com' -Path 'api/system/status' -Headers @{}
    } 'remote Sonar endpoint rejection'

    $lockContext = [pscustomobject]@{ BaseDirectory = $tempRoot; LockPath = Join-Path $tempRoot 'audit.lock' }
    $lock = Enter-QualityLock -Context $lockContext -Operation 'test' -RunId 'module-check' -TimeoutSeconds 1
    try {
        Assert-Throws { Enter-QualityLock -Context $lockContext -Operation 'test' -RunId 'contender' -TimeoutSeconds 1 } 'exclusive lock'
    }
    finally { Exit-QualityLock -Lock $lock }
    $released = Enter-QualityLock -Context $lockContext -Operation 'test' -RunId 'after-release' -TimeoutSeconds 1
    Exit-QualityLock -Lock $released

    if ($IsWindows) {
        $secretContext = [pscustomobject]@{ SecretsDirectory = Join-Path $tempRoot 'encrypted-secrets' }
        Set-QualitySecret -Context $secretContext -Name 'module-test-only' -Value $secret
        $secretPath = Get-QualitySecretPath -Context $secretContext -Name 'module-test-only'
        if ([IO.File]::ReadAllText($secretPath).Contains($secret)) { throw 'DPAPI secret file contains plaintext.' }
        Assert-Equal (Get-QualitySecret -Context $secretContext -Name 'module-test-only') $secret 'DPAPI round trip'
        Remove-QualitySecret -Context $secretContext -Name 'module-test-only'
    }
}
finally { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host "Test-SonarQualityModule: $passed assertions passed."
