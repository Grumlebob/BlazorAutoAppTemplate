[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('BlazorAuto', 'React')][string]$FrontendProfile,
    [string]$ProjectKey,
    [string]$SettingsPath
)

$ErrorActionPreference = 'Stop'
$tokenBefore = [Environment]::GetEnvironmentVariable('SONARQUBE_TOKEN', 'Process')
$started = $false
try {
    Import-Module (Join-Path $PSScriptRoot 'SonarQuality.psm1') -Force -DisableNameChecking
    $repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
    $context = Get-QualityContext -RepoRoot $repoRoot -SettingsPath $SettingsPath
    $mainProjectKey = [string]$context.ProjectKeys.$FrontendProfile
    if (-not $ProjectKey) { $ProjectKey = $mainProjectKey }
    if ($ProjectKey -notmatch "^$([regex]::Escape($mainProjectKey))(-candidate-[0-9a-f]{12})?$") {
        throw 'Project key must be this repository profile main project or an owned candidate key.'
    }
    if (-not $context.DockerExecutable) { throw 'Docker CLI was not found.' }

    $composeEnvironment = @{
        SONARQUBE_DB_PASSWORD = 'quality-mcp-ownership-probe'
        SONARQUBE_HOST_PORT = [string]$context.HostPort
        SONARQUBE_IDENTITY_HASH = $context.IdentityHash
        SONARQUBE_NETWORK_NAME = $context.ComposeNetwork
        SONARQUBE_COMPOSE_PROJECT = $context.ComposeProject
    }
    $containerCheck = Invoke-QualityProcess -FilePath $context.DockerExecutable `
        -ArgumentList @('compose', '--project-name', $context.ComposeProject, '--file', $context.ComposePath, 'ps', '-q', 'sonarqube') `
        -WorkingDirectory $context.BaseDirectory -TimeoutSeconds 20 -Environment $composeEnvironment
    if ($containerCheck.TimedOut -or $containerCheck.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($containerCheck.Stdout)) {
        throw 'The repository-owned SonarQube container is not running. Start it with SonarQubeServer.ps1 -Start.'
    }
    $publishedPort = Invoke-QualityProcess -FilePath $context.DockerExecutable `
        -ArgumentList @('compose', '--project-name', $context.ComposeProject, '--file', $context.ComposePath, 'port', 'sonarqube', '9000') `
        -WorkingDirectory $context.BaseDirectory -TimeoutSeconds 20 -Environment $composeEnvironment
    if ($publishedPort.TimedOut -or $publishedPort.ExitCode -ne 0 -or
        $publishedPort.Stdout.Trim() -ne "127.0.0.1:$($context.HostPort)") {
        throw 'The owned SonarQube port does not match private repository settings; preserve the stack and inspect local state.'
    }

    try { $status = (Invoke-RestMethod -Uri "$($context.BaseUrl)/api/system/status" -TimeoutSec 5).status }
    catch { throw 'The repository-owned SonarQube stack is not reachable. Start it with SonarQubeServer.ps1 -Start.' }
    if ($status -ne 'UP') { throw "The repository-owned SonarQube stack is not ready (status '$status')." }

    $readerToken = Get-QualitySecret -Context $context -Name "reader-$($FrontendProfile.ToLowerInvariant())-token"
    $auth = New-QualityAuthHeader -Token $readerToken
    $validation = Invoke-QualityApi -BaseUrl $context.BaseUrl -Path 'api/authentication/validate' `
        -Headers $auth -RedactValues @($readerToken)
    if ($validation.valid -ne $true) { throw 'The profile reader token is not valid.' }

    [Environment]::SetEnvironmentVariable('SONARQUBE_TOKEN', $readerToken, 'Process')
    $started = $true
    $probeContainer = [Environment]::GetEnvironmentVariable('SONAR_QUALITY_MCP_PROBE_CONTAINER', 'Process')
    $arguments = @('run', '--init', '-i', '--rm')
    if ($probeContainer) {
        if ($probeContainer -notmatch '^quality-mcp-probe-[0-9a-f]{16}$') { throw 'Invalid private MCP probe container name.' }
        $existingProbe = Invoke-QualityProcess -FilePath $context.DockerExecutable `
            -ArgumentList @('container', 'inspect', $probeContainer) `
            -WorkingDirectory $context.BaseDirectory -TimeoutSeconds 15
        if ($existingProbe.TimedOut) { throw 'Could not verify the private MCP probe container name is unused.' }
        if ($existingProbe.ExitCode -eq 0) { throw 'The private MCP probe container name already exists; preserve it and inspect local state.' }
        if ($existingProbe.ExitCode -ne 1 -or $existingProbe.Stderr -notmatch 'No such (object|container)') {
            throw 'Could not verify the private MCP probe container name is unused.'
        }
        $arguments += @('--name', $probeContainer)
    }
    $arguments += @(
        '--network', $context.ComposeNetwork,
        '-e', 'SONARQUBE_TOKEN',
        '-e', 'SONARQUBE_URL=http://sonarqube:9000',
        '-e', "SONARQUBE_PROJECT_KEY=$ProjectKey",
        '-e', 'SONARQUBE_READ_ONLY=true',
        '-e', 'SONARQUBE_TOOLSETS=issues,measures,quality-gates,rules,duplications,coverage,security-hotspots',
        '-e', 'SONARQUBE_LOG_TO_FILE_DISABLED=true',
        '-e', 'TELEMETRY_DISABLED=true',
        [string]$context.ToolVersions.mcpImage
    )
    & $context.DockerExecutable @arguments
    $dockerExit = $LASTEXITCODE
    if ($dockerExit -ne 0) { throw "The pinned SonarQube MCP container exited with code $dockerExit." }
}
catch {
    [Console]::Error.WriteLine("sonarqube-mcp: $($_.Exception.Message)")
    exit 1
}
finally {
    if ($started) { [Environment]::SetEnvironmentVariable('SONARQUBE_TOKEN', $tokenBefore, 'Process') }
}
