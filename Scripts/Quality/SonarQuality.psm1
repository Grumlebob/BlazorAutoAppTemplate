Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-QualityToolVersions {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)

    $path = Join-Path $RepoRoot 'Scripts/Quality/tool-versions.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Pinned quality tool manifest is missing: $path"
    }
    $versions = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json -AsHashtable
    if ($versions.schema -ne 'blazorautoapp.sonar-tools/1') {
        throw "Unsupported quality tool manifest schema '$($versions.schema)'."
    }
    return $versions
}

function ConvertTo-RepositoryIdentity {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$OriginUrl)

    $source = $OriginUrl.Trim()
    if ([string]::IsNullOrWhiteSpace($source)) { throw 'Git origin URL is empty.' }

    $hostName = $null
    $repositoryPath = $null
    if ($source -match '^[^/@:]+@(?<host>[^:]+):(?<path>.+)$' -and $source -notmatch '://') {
        $hostName = $Matches.host
        $repositoryPath = $Matches.path
    }
    else {
        $uri = $null
        if (-not [Uri]::TryCreate($source, [UriKind]::Absolute, [ref]$uri)) {
            throw 'Git origin must be an absolute HTTPS, HTTP, SSH, or Git URL.'
        }
        if ($uri.Scheme -notin @('https', 'http', 'ssh', 'git')) {
            throw "Unsupported Git origin scheme '$($uri.Scheme)'."
        }
        $hostName = $uri.Host
        $repositoryPath = $uri.AbsolutePath
    }

    $hostName = $hostName.Trim().TrimEnd('.').ToLowerInvariant()
    $repositoryPath = $repositoryPath.Trim().Trim('/')
    if ($repositoryPath.EndsWith('.git', [StringComparison]::OrdinalIgnoreCase)) {
        $repositoryPath = $repositoryPath.Substring(0, $repositoryPath.Length - 4)
    }
    $segments = @($repositoryPath.Split('/', [StringSplitOptions]::RemoveEmptyEntries))
    $unsafeSegments = @($segments | Where-Object { $_ -in @('.', '..') -or $_ -match '[\x00-\x1f]' })
    if ([string]::IsNullOrWhiteSpace($hostName) -or $segments.Count -lt 2 -or $unsafeSegments.Count -gt 0) {
        throw 'Git origin must identify a host, owner, and repository.'
    }

    if ($hostName -eq 'github.com') { $segments = @($segments | ForEach-Object { $_.ToLowerInvariant() }) }
    $normalizedPath = $segments -join '/'
    return "$hostName/$normalizedPath"
}

function Get-QualityRepositoryIdentity {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)

    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = (Get-Command git.exe, git -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if ([string]::IsNullOrWhiteSpace($start.FileName)) { throw 'Git executable was not found.' }
    $start.WorkingDirectory = [IO.Path]::GetFullPath($RepoRoot)
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.ArgumentList.Add('remote')
    $start.ArgumentList.Add('get-url')
    $start.ArgumentList.Add('origin')
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'Git did not start.' }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) {
            $process.Kill($true)
            throw 'Timed out reading Git origin.'
        }
        $stdout = $stdoutTask.GetAwaiter().GetResult().Trim()
        $stderr = $stderrTask.GetAwaiter().GetResult().Trim()
        if ($process.ExitCode -ne 0) {
            $safeError = Protect-QualityText -Text $stderr
            throw "Could not read Git origin (exit $($process.ExitCode)): $safeError"
        }
        return ConvertTo-RepositoryIdentity -OriginUrl $stdout
    }
    finally { $process.Dispose() }
}

function Get-QualityBaseDirectory {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepositorySlug, [Parameter(Mandatory)][string]$IdentityHash8)

    $root = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($root)) { $root = $env:XDG_DATA_HOME }
    if ([string]::IsNullOrWhiteSpace($root)) {
        if ([string]::IsNullOrWhiteSpace($HOME)) { throw 'No per-user data directory is available.' }
        $root = Join-Path $HOME '.local/share'
    }
    return [IO.Path]::GetFullPath((Join-Path $root "BlazorAutoAppQuality/SonarQube/$RepositorySlug-$IdentityHash8"))
}

function Get-QualitySettingsDocument {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Settings file does not exist: $Path" }
    try { $settings = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable }
    catch { throw "Settings file is not valid JSON: $Path" }
    $allowed = @('schema', 'hostPort', 'nodeToolchainDirectory', 'pythonExecutable')
    $unknown = @($settings.Keys | Where-Object { $_ -notin $allowed })
    if ($unknown.Count -gt 0) { throw "Unknown quality setting(s): $($unknown -join ', ')" }
    if ($settings.schema -ne 'blazorautoapp.sonar-settings/1') {
        throw "Unsupported settings schema '$($settings.schema)'."
    }
    if ($null -ne $settings.hostPort) {
        if (($settings.hostPort -isnot [int] -and $settings.hostPort -isnot [long]) -or $settings.hostPort -lt 1 -or $settings.hostPort -gt 65535) {
            throw 'hostPort must be null or an integer from 1 through 65535.'
        }
        $settings.hostPort = [int]$settings.hostPort
    }
    foreach ($name in @('nodeToolchainDirectory', 'pythonExecutable')) {
        if ($null -ne $settings[$name] -and $settings[$name] -isnot [string]) {
            throw "$name must be null or a string."
        }
    }
    return $settings
}

function Get-QualityPrivateSettings {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$RepositoryIdentity,
        [Parameter(Mandatory)][string]$IdentityHash
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try { $settings = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable }
    catch { throw "Private quality settings are not valid JSON: $Path" }
    $allowed = @('schema', 'repositoryIdentity', 'identityHash', 'hostPort', 'createdUtc')
    $unknown = @($settings.Keys | Where-Object { $_ -notin $allowed })
    if ($unknown.Count -gt 0) { throw "Unknown private quality setting(s): $($unknown -join ', ')" }
    if ($settings.schema -ne 'blazorautoapp.sonar-private-settings/1' -or
        $settings.repositoryIdentity -ne $RepositoryIdentity -or $settings.identityHash -ne $IdentityHash) {
        throw 'Private quality settings identity does not match this Git origin; refusing to reuse the namespace.'
    }
    if ($settings.identityHash -notmatch '^[0-9a-f]{64}$') { throw 'Private quality settings contain an invalid identity hash.' }
    if (($settings.hostPort -isnot [int] -and $settings.hostPort -isnot [long]) -or $settings.hostPort -lt 1 -or $settings.hostPort -gt 65535) {
        throw 'Private quality settings contain an invalid hostPort.'
    }
    $settings.hostPort = [int]$settings.hostPort
    return $settings
}

function Test-QualityPortAvailable {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port)

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Server.ExclusiveAddressUse = $true
        $listener.Start()
        return $true
    }
    catch { return $false }
    finally { $listener.Stop() }
}

function Get-QualityNodeRuntime {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$ToolVersions, [string]$ConfiguredDirectory)

    $version = [string]$ToolVersions.node.version
    $candidates = [Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($ConfiguredDirectory)) {
        $configured = [IO.Path]::GetFullPath($ConfiguredDirectory)
        $candidates.Add((Join-Path $configured 'node.exe'))
        $candidates.Add((Join-Path $configured 'bin/node.exe'))
    }
    foreach ($command in @(Get-Command node.exe, node -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($command.Source) { $candidates.Add($command.Source) }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA "Programs/nodejs/v$version/node.exe"))
    }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($node in $candidates) {
        if (-not $seen.Add($node) -or -not (Test-Path -LiteralPath $node -PathType Leaf)) { continue }
        $nodeDirectory = Split-Path -Parent $node
        $npmCli = Join-Path $nodeDirectory 'node_modules/npm/bin/npm-cli.js'
        if (-not (Test-Path -LiteralPath $npmCli -PathType Leaf)) { continue }
        $probe = [Diagnostics.ProcessStartInfo]::new()
        $probe.FileName = $node
        $probe.UseShellExecute = $false
        $probe.RedirectStandardOutput = $true
        $probe.RedirectStandardError = $true
        $probe.ArgumentList.Add('--version')
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $probe
        try {
            if (-not $process.Start()) { continue }
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(10000)) { $process.Kill($true); continue }
            $actual = $stdoutTask.GetAwaiter().GetResult().Trim().TrimStart('v')
            $null = $stderrTask.GetAwaiter().GetResult()
            if ($process.ExitCode -eq 0 -and $actual -eq $version) {
                $npmProbe = [Diagnostics.ProcessStartInfo]::new()
                $npmProbe.FileName = $node
                $npmProbe.UseShellExecute = $false
                $npmProbe.RedirectStandardOutput = $true
                $npmProbe.RedirectStandardError = $true
                $npmProbe.ArgumentList.Add($npmCli)
                $npmProbe.ArgumentList.Add('--version')
                $npmProcess = [Diagnostics.Process]::new()
                $npmProcess.StartInfo = $npmProbe
                try {
                    if (-not $npmProcess.Start()) { continue }
                    $npmOut = $npmProcess.StandardOutput.ReadToEndAsync()
                    $npmErr = $npmProcess.StandardError.ReadToEndAsync()
                    if (-not $npmProcess.WaitForExit(15000)) { $npmProcess.Kill($true); continue }
                    $npmVersion = $npmOut.GetAwaiter().GetResult().Trim()
                    $null = $npmErr.GetAwaiter().GetResult()
                    if ($npmProcess.ExitCode -eq 0 -and $npmVersion -eq [string]$ToolVersions.node.npmVersion) {
                        return [pscustomobject]@{ NodeExecutable = [IO.Path]::GetFullPath($node); NpmCli = [IO.Path]::GetFullPath($npmCli); Directory = $nodeDirectory; NodeVersion = $actual; NpmVersion = $npmVersion }
                    }
                }
                finally { $npmProcess.Dispose() }
            }
        }
        catch { }
        finally { $process.Dispose() }
    }
    throw "Pinned Node $version and npm $($ToolVersions.node.npmVersion) were not found. Run the documented user-local tool setup or set nodeToolchainDirectory in ignored quality settings."
}

function Get-QualityPythonExecutable {
    [CmdletBinding()]
    param([string]$ConfiguredExecutable)

    $candidates = [Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($ConfiguredExecutable)) { $candidates.Add([IO.Path]::GetFullPath($ConfiguredExecutable)) }
    foreach ($command in @(Get-Command python.exe, python -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($command.Source -and $command.Source -notmatch '[\\/]WindowsApps[\\/]') { $candidates.Add($command.Source) }
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $probe = [Diagnostics.ProcessStartInfo]::new()
        $probe.FileName = $candidate
        $probe.UseShellExecute = $false
        $probe.RedirectStandardOutput = $true
        $probe.RedirectStandardError = $true
        $probe.ArgumentList.Add('--version')
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $probe
        try {
            if (-not $process.Start()) { continue }
            $stdout = $process.StandardOutput.ReadToEndAsync()
            $stderr = $process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(10000)) { $process.Kill($true); continue }
            $version = ($stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()).Trim()
            if ($process.ExitCode -eq 0 -and $version -match '^Python 3\.') { return [IO.Path]::GetFullPath($candidate) }
        }
        finally { $process.Dispose() }
    }
    throw 'Python 3 executable was not found. Set pythonExecutable in ignored quality settings.'
}

function Get-QualityContext {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$SettingsPath,
        [switch]$RequireReactToolchain
    )

    $repo = (Resolve-Path -LiteralPath $RepoRoot).Path
    $identity = Get-QualityRepositoryIdentity -RepoRoot $repo
    $hashBytes = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($identity))
    $identityHash = [Convert]::ToHexString($hashBytes).ToLowerInvariant()
    $slug = [regex]::Replace(($identity.Split('/')[-1]).ToLowerInvariant(), '[^a-z0-9]+', '-').Trim('-')
    if ([string]::IsNullOrWhiteSpace($slug)) { throw 'Git origin repository name cannot form a safe project slug.' }
    if ($slug.Length -gt 48) { $slug = $slug.Substring(0, 48).Trim('-') }
    $hash8 = $identityHash.Substring(0, 8)
    $composeProject = "sonarqube-$slug-$hash8"
    $baseDirectory = Get-QualityBaseDirectory -RepositorySlug $slug -IdentityHash8 $hash8
    $privateSettingsPath = Join-Path $baseDirectory 'settings.json'
    $privateSettings = Get-QualityPrivateSettings -Path $privateSettingsPath -RepositoryIdentity $identity -IdentityHash $identityHash

    $defaultPath = Join-Path $repo 'Scripts/Quality/quality-settings.example.json'
    $defaults = Get-QualitySettingsDocument -Path $defaultPath
    $settingsSources = [Collections.Generic.List[hashtable]]::new()
    if (-not [string]::IsNullOrWhiteSpace($SettingsPath)) {
        $resolvedSettingsPath = if ([IO.Path]::IsPathRooted($SettingsPath)) { $SettingsPath } else { Join-Path $repo $SettingsPath }
        $settingsSources.Add((Get-QualitySettingsDocument -Path ([IO.Path]::GetFullPath($resolvedSettingsPath))))
    }
    else {
        $localPath = Join-Path $repo 'Scripts/Quality/quality-settings.local.json'
        if (Test-Path -LiteralPath $localPath -PathType Leaf) { $settingsSources.Add((Get-QualitySettingsDocument -Path $localPath)) }
    }
    $settingsSources.Add($defaults)

    $settingValues = @{}
    foreach ($name in @('hostPort', 'nodeToolchainDirectory', 'pythonExecutable')) {
        $settingValues[$name] = $null
        foreach ($source in $settingsSources) {
            if ($source.ContainsKey($name) -and $null -ne $source[$name]) { $settingValues[$name] = $source[$name]; break }
        }
    }

    $explicitPort = $settingValues.hostPort
    if ($null -ne $privateSettings) {
        if ($null -ne $explicitPort -and $explicitPort -ne $privateSettings.hostPort) {
            throw "This repository already uses loopback port $($privateSettings.hostPort); refusing an implicit port change."
        }
        $hostPort = [int]$privateSettings.hostPort
    }
    elseif ($null -ne $explicitPort) {
        $hostPort = [int]$explicitPort
    }
    else { $hostPort = 9200 }

    $versions = Get-QualityToolVersions -RepoRoot $repo
    $python = Get-QualityPythonExecutable -ConfiguredExecutable $settingValues.pythonExecutable
    $node = if ($RequireReactToolchain) { Get-QualityNodeRuntime -ToolVersions $versions -ConfiguredDirectory $settingValues.nodeToolchainDirectory } else { $null }
    $dotnetCommand = Get-Command dotnet.exe, dotnet -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $gitCommand = Get-Command git.exe, git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $dotnetCommand -or -not $dotnetCommand.Source) { throw '.NET SDK executable was not found.' }
    if (-not $gitCommand -or -not $gitCommand.Source) { throw 'Git executable was not found.' }
    $dockerCommand = Get-Command docker.exe, docker -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $effectiveSettings = [ordered]@{
        schema = 'blazorautoapp.sonar-settings/1'
        hostPort = $hostPort
        nodeToolchainConfigured = [bool]$settingValues.nodeToolchainDirectory
        pythonExecutableConfigured = [bool]$settingValues.pythonExecutable
    }
    $effectiveJson = $effectiveSettings | ConvertTo-Json -Depth 4 -Compress
    $settingsDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($effectiveJson))).ToLowerInvariant()
    $baseUrl = "http://127.0.0.1:$hostPort"
    return [pscustomobject]@{
        RepoRoot = $repo
        RepositoryIdentity = $identity
        IdentityHash = $identityHash
        IdentityHash8 = $hash8
        RepositorySlug = $slug
        ComposeProject = $composeProject
        ComposeNetwork = "$composeProject-network"
        ProjectKeys = [pscustomobject]@{ BlazorAuto = "$slug-$hash8-BlazorAuto"; React = "$slug-$hash8-React" }
        BaseDirectory = $baseDirectory
        PrivateSettingsPath = $privateSettingsPath
        SecretsDirectory = Join-Path $baseDirectory 'secrets'
        ToolsDirectory = Join-Path $baseDirectory 'tools'
        ReportsDirectory = Join-Path $baseDirectory 'reports'
        RunsDirectory = Join-Path $baseDirectory 'runs'
        LockPath = Join-Path $baseDirectory 'audit.lock'
        HostPort = $hostPort
        BaseUrl = $baseUrl
        ComposePath = Join-Path $repo 'docker/sonarqube/compose.yaml'
        ToolVersions = $versions
        DotnetExecutable = [IO.Path]::GetFullPath($dotnetCommand.Source)
        GitExecutable = [IO.Path]::GetFullPath($gitCommand.Source)
        DockerExecutable = if ($dockerCommand -and $dockerCommand.Source) { [IO.Path]::GetFullPath($dockerCommand.Source) } else { $null }
        PythonExecutable = $python
        NodeExecutable = if ($node) { $node.NodeExecutable } else { $null }
        NpmCli = if ($node) { $node.NpmCli } else { $null }
        NodeVersion = if ($node) { $node.NodeVersion } else { $null }
        NpmVersion = if ($node) { $node.NpmVersion } else { $null }
        SettingsSnapshot = $effectiveJson
        SettingsDigest = $settingsDigest
        PrivateSettings = $privateSettings
        LocalSettingsPath = if ($SettingsPath) { $resolvedSettingsPath } else { Join-Path $repo 'Scripts/Quality/quality-settings.local.json' }
    }
}

function Resolve-QualityHostPort {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context)

    if ($Context.PrivateSettings) {
        if (-not (Test-QualityPortAvailable -Port ([int]$Context.HostPort))) {
            # An occupied persisted port can be the already-running owned server.
            return [int]$Context.HostPort
        }
        return [int]$Context.HostPort
    }

    $configuredPort = $null
    if (Test-Path -LiteralPath $Context.LocalSettingsPath -PathType Leaf) {
        $settings = Get-QualitySettingsDocument -Path $Context.LocalSettingsPath
        $configuredPort = $settings.hostPort
    }
    if ($null -ne $configuredPort) {
        if (-not (Test-QualityPortAvailable -Port ([int]$configuredPort))) { throw "Configured loopback port $configuredPort is occupied." }
        Set-QualityHostPort -Context $Context -Port ([int]$configuredPort)
        return $Context.HostPort
    }

    foreach ($candidate in 9200..9299) {
        if (Test-QualityPortAvailable -Port $candidate) {
            Set-QualityHostPort -Context $Context -Port $candidate
            return $candidate
        }
    }
    throw 'No free loopback port exists in 9200–9299; set hostPort in ignored quality settings.'
}

function Set-QualityHostPort {
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port)
    $Context.HostPort = $Port
    $Context.BaseUrl = "http://127.0.0.1:$Port"
    $settings = $Context.SettingsSnapshot | ConvertFrom-Json -AsHashtable
    $settings.hostPort = $Port
    $json = $settings | ConvertTo-Json -Depth 4 -Compress
    $Context.SettingsSnapshot = $json
    $Context.SettingsDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($json))).ToLowerInvariant()
}

function Save-QualityPrivateSettings {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context)

    New-Item -ItemType Directory -Force -Path $Context.BaseDirectory | Out-Null
    if ($Context.PrivateSettings) {
        if ($Context.PrivateSettings.repositoryIdentity -ne $Context.RepositoryIdentity -or
            $Context.PrivateSettings.identityHash -ne $Context.IdentityHash -or
            $Context.PrivateSettings.hostPort -ne $Context.HostPort) {
            throw 'Refusing to replace private quality settings with a different identity or port.'
        }
        return
    }
    $document = [ordered]@{
        schema = 'blazorautoapp.sonar-private-settings/1'
        repositoryIdentity = $Context.RepositoryIdentity
        identityHash = $Context.IdentityHash
        hostPort = $Context.HostPort
        createdUtc = [DateTime]::UtcNow.ToString('o')
    }
    $temporaryPath = "$($Context.PrivateSettingsPath).$([guid]::NewGuid().ToString('N')).tmp"
    try {
        $json = $document | ConvertTo-Json -Depth 4
        [IO.File]::WriteAllText($temporaryPath, $json, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporaryPath -Destination $Context.PrivateSettingsPath
        $Context.PrivateSettings = $document
    }
    finally { Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue }
}

function Enter-QualityLock {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Context,
        [Parameter(Mandatory)][string]$Operation,
        [Parameter(Mandatory)][string]$RunId,
        [ValidateRange(1, 300)][int]$TimeoutSeconds = 30
    )

    New-Item -ItemType Directory -Force -Path $Context.BaseDirectory | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $stream = [IO.FileStream]::new($Context.LockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
            $stream.SetLength(0)
            $metadata = [ordered]@{ processId = $PID; operation = $Operation; runId = $RunId; startedUtc = [DateTime]::UtcNow.ToString('o') } | ConvertTo-Json -Compress
            $bytes = [Text.Encoding]::UTF8.GetBytes($metadata)
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Flush($true)
            return [pscustomobject]@{ Path = $Context.LockPath; Stream = $stream; RunId = $RunId }
        }
        catch [IO.IOException] {
            if ([DateTime]::UtcNow -ge $deadline) {
                throw "Another quality audit or lifecycle action owns the lock. Wait for it to finish; lock metadata is at $($Context.LockPath)."
            }
            Start-Sleep -Milliseconds 250
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Timed out waiting for the quality audit lock.'
}

function Exit-QualityLock {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Lock)
    if ($Lock.Stream) { $Lock.Stream.Dispose() }
}

function Protect-QualityText {
    [CmdletBinding()]
    param([AllowEmptyString()][string]$Text, [string[]]$Secrets = @())

    $safe = [string]$Text
    foreach ($secret in @($Secrets | Where-Object { -not [string]::IsNullOrEmpty($_) } | Sort-Object Length -Descending)) {
        $safe = $safe.Replace($secret, '[REDACTED]')
    }
    $safe = [regex]::Replace($safe, '(?i)(https?://)[^/@\s]+@', '$1[REDACTED]@')
    $safe = [regex]::Replace($safe, '(?i)(/d:)?sonar\.(token|login|password)=([^\s"'']+)', '$1sonar.$2=[REDACTED]')
    $safe = [regex]::Replace($safe, '(?i)(authorization\s*[:=]\s*(?:bearer|basic)\s+)[^\s"'']+', '$1[REDACTED]')
    return $safe
}

function ConvertTo-QualityDisplayArguments {
    [CmdletBinding()]
    param([string[]]$Arguments)
    return @($Arguments | ForEach-Object { Protect-QualityText -Text $_ })
}

function Invoke-QualityProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [ValidateRange(1, 5400)][int]$TimeoutSeconds = 1200,
        [hashtable]$Environment = @{},
        [string[]]$RedactValues = @(),
        [string]$OutputDirectory,
        [string]$StepName = 'process'
    )

    $resolvedExecutable = [IO.Path]::GetFullPath($FilePath)
    $resolvedWorkingDirectory = [IO.Path]::GetFullPath($WorkingDirectory)
    if (-not (Test-Path -LiteralPath $resolvedExecutable -PathType Leaf)) { throw "Executable does not exist: $resolvedExecutable" }
    if (-not (Test-Path -LiteralPath $resolvedWorkingDirectory -PathType Container)) { throw "Working directory does not exist: $resolvedWorkingDirectory" }

    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $resolvedExecutable
    $start.WorkingDirectory = $resolvedWorkingDirectory
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $ArgumentList) { $start.ArgumentList.Add([string]$argument) }
    foreach ($name in $Environment.Keys) {
        if ($null -eq $Environment[$name]) { $start.Environment.Remove([string]$name) | Out-Null }
        else { $start.Environment[[string]$name] = [string]$Environment[$name] }
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $startedUtc = [DateTime]::UtcNow
    try {
        if (-not $process.Start()) { throw 'ProcessStartInfo.Start returned false.' }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $timedOut = -not $process.WaitForExit([Math]::Min([int]::MaxValue, $TimeoutSeconds * 1000))
        if ($timedOut) {
            try { $process.Kill($true) } catch { }
            $process.WaitForExit()
        }
        $stdout = Protect-QualityText -Text $stdoutTask.GetAwaiter().GetResult() -Secrets $RedactValues
        $stderr = Protect-QualityText -Text $stderrTask.GetAwaiter().GetResult() -Secrets $RedactValues
        $exitCode = if ($timedOut) { $null } else { $process.ExitCode }
        if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
            New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
            $safeStep = [regex]::Replace($StepName, '[^A-Za-z0-9._-]', '_')
            [IO.File]::WriteAllText((Join-Path $OutputDirectory "$safeStep.stdout.log"), $stdout, [Text.UTF8Encoding]::new($false))
            [IO.File]::WriteAllText((Join-Path $OutputDirectory "$safeStep.stderr.log"), $stderr, [Text.UTF8Encoding]::new($false))
        }
        return [pscustomobject]@{
            Executable = $resolvedExecutable
            Arguments = [string[]](ConvertTo-QualityDisplayArguments -Arguments $ArgumentList)
            WorkingDirectory = $resolvedWorkingDirectory
            ExitCode = $exitCode
            TimedOut = $timedOut
            Stdout = $stdout
            Stderr = $stderr
            StartedUtc = $startedUtc.ToString('o')
            FinishedUtc = [DateTime]::UtcNow.ToString('o')
            DurationSeconds = [Math]::Round(([DateTime]::UtcNow - $startedUtc).TotalSeconds, 3)
        }
    }
    catch {
        $safe = Protect-QualityText -Text $_.Exception.Message -Secrets $RedactValues
        throw "Could not run '$resolvedExecutable': $safe"
    }
    finally { $process.Dispose() }
}

function Test-QualityPathWithinRoot {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Root)

    $fullRoot = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $comparison = if ($IsWindows) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
    return $fullPath.Equals($fullRoot, $comparison) -or $fullPath.StartsWith($fullRoot + [IO.Path]::DirectorySeparatorChar, $comparison)
}

function Assert-QualitySafeChildPath {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Root)

    if (-not (Test-QualityPathWithinRoot -Path $Path -Root $Root)) { throw "Refusing path outside owned root: $Path" }
    $segments = ([IO.Path]::GetFullPath($Path) -split '[\\/]') | Where-Object { $_ }
    $reserved = @($segments | Where-Object { $_ -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$' })
    if ($reserved.Count -gt 0) { throw "Reserved Windows path is not allowed: $($reserved[0])" }
    return [IO.Path]::GetFullPath($Path)
}

function Remove-QualityScannerState {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot, [Parameter(Mandatory)][string]$ExpectedRunRoot)

    $scannerPath = Assert-QualitySafeChildPath -Path (Join-Path $RepoRoot '.sonarqube') -Root $RepoRoot
    if (-not (Test-Path -LiteralPath $scannerPath)) { return }
    if (-not (Test-QualityPathWithinRoot -Path $scannerPath -Root $ExpectedRunRoot)) {
        throw "Scanner state is outside this run's owned worktree: $scannerPath"
    }
    Remove-Item -LiteralPath $scannerPath -Recurse -Force
}

function Get-QualitySecretPath {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][string]$Name)

    if ($Name -notmatch '^[a-z0-9][a-z0-9._-]{0,119}$') { throw 'Invalid owned secret name.' }
    $path = Join-Path $Context.SecretsDirectory "$Name.clixml"
    return Assert-QualitySafeChildPath -Path $path -Root $Context.SecretsDirectory
}

function Set-QualitySecret {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Value)

    if (-not $IsWindows) { throw 'Full-mode secrets use Windows DPAPI; run provisioning in PowerShell 7 on Windows.' }
    New-Item -ItemType Directory -Force -Path $Context.SecretsDirectory | Out-Null
    $target = Get-QualitySecretPath -Context $Context -Name $Name
    $temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        ConvertTo-SecureString -String $Value -AsPlainText -Force | Export-Clixml -Path $temporary
        Move-Item -LiteralPath $temporary -Destination $target -Force
    }
    finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
}

function Get-QualitySecret {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][string]$Name, [switch]$Optional)

    if (-not $IsWindows) { throw 'Full-mode secrets use Windows DPAPI; run provisioning in PowerShell 7 on Windows.' }
    $path = Get-QualitySecretPath -Context $Context -Name $Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        if ($Optional) { return $null }
        throw "Owned encrypted quality secret '$Name' is missing. Run the documented initialization command."
    }
    return (Import-Clixml -Path $path | ConvertFrom-SecureString -AsPlainText)
}

function Test-QualitySecret {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][string]$Name)
    return Test-Path -LiteralPath (Get-QualitySecretPath -Context $Context -Name $Name) -PathType Leaf
}

function Remove-QualitySecret {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [Parameter(Mandatory)][string]$Name)
    Remove-Item -LiteralPath (Get-QualitySecretPath -Context $Context -Name $Name) -Force -ErrorAction SilentlyContinue
}

function New-QualityPassword {
    [CmdletBinding()]
    param([ValidateRange(24, 128)][int]$Length = 40)

    $sets = @('ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '!#%+-=_')
    $all = -join $sets
    $characters = [Collections.Generic.List[char]]::new()
    foreach ($set in $sets) { $characters.Add($set[[Security.Cryptography.RandomNumberGenerator]::GetInt32($set.Length)]) }
    while ($characters.Count -lt $Length) { $characters.Add($all[[Security.Cryptography.RandomNumberGenerator]::GetInt32($all.Length)]) }
    for ($index = $characters.Count - 1; $index -gt 0; $index--) {
        $swap = [Security.Cryptography.RandomNumberGenerator]::GetInt32($index + 1)
        $temporary = $characters[$index]
        $characters[$index] = $characters[$swap]
        $characters[$swap] = $temporary
    }
    return -join $characters
}

function New-QualityAuthHeader {
    [CmdletBinding()]
    param([string]$Token, [string]$User, [string]$Password)
    if (-not [string]::IsNullOrWhiteSpace($Token)) { return @{ Authorization = "Bearer $Token" } }
    if ([string]::IsNullOrWhiteSpace($User) -or [string]::IsNullOrWhiteSpace($Password)) { throw 'Token or complete user/password credentials are required.' }
    $pair = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${User}:${Password}"))
    return @{ Authorization = "Basic $pair" }
}

function Invoke-QualityApi {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [ValidateSet('GET', 'POST', 'PATCH', 'DELETE')][string]$Method = 'GET',
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][hashtable]$Headers,
        [hashtable]$Query,
        [hashtable]$Form,
        [object]$Json,
        [switch]$AllowNotFound,
        [ValidateRange(1, 120)][int]$TimeoutSeconds = 30,
        [string[]]$RedactValues = @()
    )

    $base = [Uri]::new($BaseUrl)
    if ($base.Scheme -ne 'http' -or $base.Host -notin @('127.0.0.1', 'localhost', '::1')) {
        throw 'Quality API is restricted to an HTTP loopback endpoint.'
    }
    $builder = [UriBuilder]::new($base)
    $builder.Path = "$($base.AbsolutePath.TrimEnd('/'))/$($Path.TrimStart('/'))"
    if ($Query) {
        $builder.Query = (($Query.GetEnumerator() | Sort-Object Key | ForEach-Object {
            '{0}={1}' -f [Uri]::EscapeDataString([string]$_.Key), [Uri]::EscapeDataString([string]$_.Value)
        }) -join '&')
    }
    $request = @{ Uri = $builder.Uri; Method = $Method; Headers = $Headers; TimeoutSec = $TimeoutSeconds; ErrorAction = 'Stop' }
    if ($Form) { $request.Body = $Form; $request.ContentType = 'application/x-www-form-urlencoded' }
    if ($null -ne $Json) { $request.Body = $Json | ConvertTo-Json -Depth 12 -Compress; $request.ContentType = 'application/json' }
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try { return Invoke-RestMethod @request }
        catch {
            $status = $null
            if ($_.Exception.PSObject.Properties['Response'] -and $_.Exception.Response) {
                try { $status = [int]$_.Exception.Response.StatusCode } catch { }
            }
            if ($AllowNotFound -and $status -eq 404) { return $null }
            $transient = $null -eq $status -or $status -eq 408 -or $status -eq 429 -or $status -ge 500
            if ($attempt -lt 3 -and $transient) { Start-Sleep -Seconds $attempt; continue }
            $detail = if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $_.ErrorDetails.Message } else { $_.Exception.Message }
            $detail = Protect-QualityText -Text $detail -Secrets $RedactValues
            throw "Quality API $Method /$($Path.TrimStart('/')) failed after $attempt attempt(s): HTTP $status $detail"
        }
    }
}

function Wait-QualityServer {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Context, [ValidateRange(1, 1800)][int]$TimeoutSeconds = 600)

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lastStatus = 'unreachable'
    while ([DateTime]::UtcNow -lt $deadline) {
        try { $lastStatus = (Invoke-RestMethod -Uri "$($Context.BaseUrl)/api/system/status" -TimeoutSec 10).status }
        catch { $lastStatus = 'unreachable' }
        if ($lastStatus -eq 'UP') { return }
        if ($lastStatus -eq 'DOWN') { throw "SonarQube reports DOWN. Inspect this repository's scoped server logs." }
        if ($lastStatus -eq 'MIGRATION_REQUIRED') { throw "SonarQube requires a database migration. Inspect this repository's scoped server logs and follow the documented recovery steps." }
        Start-Sleep -Seconds 5
    }
    throw "SonarQube did not become ready within $TimeoutSeconds seconds; last status was '$lastStatus'."
}

Export-ModuleMember -Function @(
    'Get-QualityToolVersions', 'ConvertTo-RepositoryIdentity', 'Get-QualityRepositoryIdentity',
    'Get-QualityBaseDirectory', 'Get-QualitySettingsDocument', 'Get-QualityPrivateSettings',
    'Test-QualityPortAvailable', 'Get-QualityNodeRuntime', 'Get-QualityPythonExecutable',
    'Get-QualityContext', 'Resolve-QualityHostPort', 'Save-QualityPrivateSettings', 'Enter-QualityLock', 'Exit-QualityLock',
    'Protect-QualityText', 'ConvertTo-QualityDisplayArguments', 'Invoke-QualityProcess',
    'Test-QualityPathWithinRoot', 'Assert-QualitySafeChildPath', 'Remove-QualityScannerState',
    'Get-QualitySecretPath', 'Set-QualitySecret', 'Get-QualitySecret', 'Test-QualitySecret',
    'Remove-QualitySecret', 'New-QualityPassword', 'New-QualityAuthHeader', 'Invoke-QualityApi',
    'Wait-QualityServer'
)
