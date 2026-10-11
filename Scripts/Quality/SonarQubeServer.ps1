[CmdletBinding()]
param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Logs,
    [switch]$Initialize,
    [switch]$ApplyProfile,
    [switch]$EnsureCandidate,
    [ValidateSet('BlazorAuto', 'React', 'Both')][string]$FrontendProfile = 'Both',
    [string]$CandidateSha,
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$SettingsPath,
    [object]$Context
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module -Name (Join-Path $PSScriptRoot 'SonarQuality.psm1') -Force -DisableNameChecking
$repoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$chosen = @()
if ($Start) { $chosen += 'Start' }
if ($Stop) { $chosen += 'Stop' }
if ($Status) { $chosen += 'Status' }
if ($Logs) { $chosen += 'Logs' }
if ($chosen.Count -ne 1) { throw 'Choose exactly one action: -Start, -Stop, -Status, or -Logs.' }
if (($Initialize -or $ApplyProfile -or $EnsureCandidate) -and -not $Start) { throw 'Provisioning switches require -Start.' }
$provisioning = @()
if ($Initialize) { $provisioning += 'Initialize' }
if ($ApplyProfile) { $provisioning += 'ApplyProfile' }
if ($EnsureCandidate) { $provisioning += 'EnsureCandidate' }
if ($provisioning.Count -gt 1) {
    throw 'Use only one of -Initialize, -ApplyProfile, or -EnsureCandidate with -Start.'
}
if (($Stop -or $Status -or $Logs) -and ($Initialize -or $ApplyProfile -or $EnsureCandidate)) {
    throw 'Provisioning switches cannot be combined with -Stop, -Status, or -Logs.'
}
if ($EnsureCandidate -and ($CandidateSha -notmatch '^[0-9a-f]{40}$' -or $FrontendProfile -eq 'Both')) {
    throw '-EnsureCandidate requires a full 40-character -CandidateSha and one -FrontendProfile.'
}
if (-not $EnsureCandidate -and $CandidateSha) { throw '-CandidateSha is valid only with -EnsureCandidate.' }

$standalone = $null -eq $Context
if ($standalone) {
    $Context = Get-QualityContext -RepoRoot $repoRoot -SettingsPath $SettingsPath
}
if ($Context.RepositoryIdentity -notmatch '^[^/]+/[^/]+/.+$' -or
    $Context.ComposeProject -notmatch '^sonarqube-[a-z0-9-]+-[0-9a-f]{8}$') {
    throw 'Resolved quality context has an invalid repository or Compose identity.'
}
if (-not $Context.DockerExecutable) { throw 'Docker CLI was not found.' }
$ownsLock = $false
$lock = $null
if ($standalone) {
    $lock = Enter-QualityLock -Context $Context -Operation 'ServerLifecycle' -RunId ([guid]::NewGuid().ToString('N'))
    $ownsLock = $true
}

function Write-QualityPrivateJson {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        $json = $Value | ConvertTo-Json -Depth 12
        [IO.File]::WriteAllText($temporary, $json, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    }
    finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
}

function Get-QualityFreshMarker {
    $path = Join-Path $Context.BaseDirectory 'fresh-stack.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
    try { $marker = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
    catch { throw 'The private fresh-stack recovery marker is invalid; preserve it and inspect the owned server state.' }
    if ($marker.schema -ne 'blazorautoapp.sonar-fresh-stack/1' -or
        $marker.repositoryIdentity -ne $Context.RepositoryIdentity -or
        $marker.identityHash -ne $Context.IdentityHash) {
        throw 'The private fresh-stack marker belongs to another repository identity; refusing credential recovery.'
    }
    return $marker
}

function Remove-QualityFreshMarker {
    $path = Join-Path $Context.BaseDirectory 'fresh-stack.json'
    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
}

function Get-QualityComposeEnvironment {
    param([string]$DatabasePassword)
    if ([string]::IsNullOrEmpty($DatabasePassword)) { $DatabasePassword = 'private-compose-operation-no-op' }
    return @{
        SONARQUBE_DB_PASSWORD = $DatabasePassword
        SONARQUBE_HOST_PORT = [string]$Context.HostPort
        SONARQUBE_IDENTITY_HASH = $Context.IdentityHash
        SONARQUBE_NETWORK_NAME = $Context.ComposeNetwork
        SONARQUBE_COMPOSE_PROJECT = $Context.ComposeProject
    }
}

function Invoke-QualityDocker {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [hashtable]$Environment = @{},
        [string[]]$Secrets = @(),
        [string]$StepName = 'docker'
    )
    $logRoot = Join-Path $Context.BaseDirectory 'logs'
    $step = "$StepName-$([guid]::NewGuid().ToString('N'))"
    $result = Invoke-QualityProcess -FilePath $Context.DockerExecutable -ArgumentList $Arguments `
        -WorkingDirectory $Context.BaseDirectory -TimeoutSeconds 120 -Environment $Environment `
        -RedactValues $Secrets -OutputDirectory $logRoot -StepName $step
    if ($result.TimedOut -or $result.ExitCode -ne 0) {
        $detail = $result.Stderr.Trim()
        if ([string]::IsNullOrWhiteSpace($detail)) { $detail = $result.Stdout.Trim() }
        throw "Docker command failed (exit $($result.ExitCode), timeout $($result.TimedOut)): $(Protect-QualityText -Text $detail -Secrets $Secrets)"
    }
    return $result
}

function Invoke-QualityCompose {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][AllowEmptyString()][string]$DatabasePassword,
        [string]$StepName = 'compose'
    )
    $environment = Get-QualityComposeEnvironment -DatabasePassword $DatabasePassword
    $composeArgs = @('compose', '--project-name', $Context.ComposeProject, '--file', $Context.ComposePath) + $Arguments
    return Invoke-QualityDocker -Arguments $composeArgs -Environment $environment `
        -Secrets @($DatabasePassword) -StepName $StepName
}

function Test-QualityDockerLinux {
    $probe = Invoke-QualityDocker -Arguments @('info', '--format', '{{.OSType}}') -StepName 'docker-info'
    if ($probe.Stdout.Trim() -ne 'linux') { throw 'Docker must use Linux containers for the pinned SonarQube images.' }
}

function Test-QualityDatabaseVolume {
    param([Parameter(Mandatory)][string]$DatabasePassword)
    $volumeName = "$($Context.ComposeProject)-database"
    $environment = Get-QualityComposeEnvironment -DatabasePassword $DatabasePassword
    $result = Invoke-QualityProcess -FilePath $Context.DockerExecutable -ArgumentList @('volume', 'inspect', $volumeName) `
        -WorkingDirectory $Context.BaseDirectory -TimeoutSeconds 30 -Environment $environment `
        -RedactValues @($DatabasePassword)
    if ($result.TimedOut) { throw "Timed out inspecting this repository's database volume." }
    if ($result.ExitCode -eq 0) { return $true }
    if ($result.Stderr -match '(?i)(no such volume|not found)') { return $false }
    throw "Could not inspect the owned database volume: $(Protect-QualityText -Text $result.Stderr -Secrets @($DatabasePassword))"
}

function Ensure-QualityDatabasePassword {
    $password = Get-QualitySecret -Context $Context -Name 'database-password' -Optional
    if ($password) { return $password }
    if (Test-QualityDatabaseVolume -DatabasePassword 'private-compose-probe') {
        throw 'This repository has an existing database volume but no encrypted database password. Refusing to start or reset it; recover the original local credential.'
    }
    $marker = Get-QualityFreshMarker
    if (-not $marker) {
        $marker = [ordered]@{
            schema = 'blazorautoapp.sonar-fresh-stack/1'
            repositoryIdentity = $Context.RepositoryIdentity
            identityHash = $Context.IdentityHash
            createdUtc = [DateTime]::UtcNow.ToString('o')
        }
        Write-QualityPrivateJson -Path (Join-Path $Context.BaseDirectory 'fresh-stack.json') -Value $marker
    }
    $password = New-QualityPassword
    Set-QualitySecret -Context $Context -Name 'database-password' -Value $password
    return $password
}

function Assert-QualityPortOwnership {
    param([Parameter(Mandatory)][string]$DatabasePassword)
    if (Test-QualityPortAvailable -Port ([int]$Context.HostPort)) { return }
    $composeEnvironment = Get-QualityComposeEnvironment -DatabasePassword $DatabasePassword
    $composeArgs = @('compose', '--project-name', $Context.ComposeProject, '--file', $Context.ComposePath, 'ps', '-q', 'sonarqube')
    $owned = Invoke-QualityProcess -FilePath $Context.DockerExecutable -ArgumentList $composeArgs `
        -WorkingDirectory $Context.BaseDirectory -TimeoutSeconds 30 -Environment $composeEnvironment `
        -RedactValues @($DatabasePassword)
    if ($owned.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($owned.Stdout)) { return }
    try {
        $status = (Invoke-RestMethod -Uri "$($Context.BaseUrl)/api/system/status" -TimeoutSec 3).status
    }
    catch { $status = 'unreachable' }
    throw "Loopback port $($Context.HostPort) is occupied by a server outside this repository’s Compose project (status '$status'); preserve it and set hostPort in ignored quality settings."
}

function Get-QualityApiHeaders {
    param([string]$Token, [string]$User, [string]$Password)
    return New-QualityAuthHeader -Token $Token -User $User -Password $Password
}

function Invoke-QualityAdminApi {
    param(
        [Parameter(Mandatory)][string]$Path,
        [ValidateSet('GET', 'POST', 'DELETE')][string]$Method = 'GET',
        [hashtable]$Query,
        [hashtable]$Form,
        [object]$Json
    )
    $adminPassword = Get-QualitySecret -Context $Context -Name 'admin-password'
    $headers = Get-QualityApiHeaders -User 'admin' -Password $adminPassword
    return Invoke-QualityApi -BaseUrl $Context.BaseUrl -Method $Method -Path $Path -Headers $headers `
        -Query $Query -Form $Form -Json $Json -RedactValues @($adminPassword)
}

function Test-QualityCredential {
    param([Parameter(Mandatory)][string]$User, [Parameter(Mandatory)][string]$Password)
    try {
        $headers = Get-QualityApiHeaders -User $User -Password $Password
        $result = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/authentication/validate' `
            -Headers $headers -RedactValues @($Password)
        return $result.valid -eq $true
    }
    catch { return $false }
}

function Promote-QualitySecret {
    param([Parameter(Mandatory)][string]$PendingName, [Parameter(Mandatory)][string]$ConfirmedName, [Parameter(Mandatory)][string]$Value)
    Set-QualitySecret -Context $Context -Name $ConfirmedName -Value $Value
    Remove-QualitySecret -Context $Context -Name $PendingName
}

function Ensure-QualityAdminPassword {
    $confirmed = Get-QualitySecret -Context $Context -Name 'admin-password' -Optional
    $pending = Get-QualitySecret -Context $Context -Name 'admin-password-pending' -Optional
    $fresh = $null -ne (Get-QualityFreshMarker)

    if ($confirmed -and (Test-QualityCredential -User 'admin' -Password $confirmed)) {
        if ($pending) { Remove-QualitySecret -Context $Context -Name 'admin-password-pending' }
        Remove-QualityFreshMarker
        return
    }
    if ($pending -and (Test-QualityCredential -User 'admin' -Password $pending)) {
        Promote-QualitySecret -PendingName 'admin-password-pending' -ConfirmedName 'admin-password' -Value $pending
        Remove-QualityFreshMarker
        return
    }
    if (($confirmed -or $pending) -and -not $fresh) {
        throw 'Stored admin credentials do not authenticate and the stack is not marked fresh. Preserve the existing database and recover its credential; no reset was attempted.'
    }
    if (-not $fresh) {
        throw 'No confirmed admin password or fresh-stack recovery marker exists. Refusing to rotate credentials on an existing database.'
    }
    if (-not $pending) {
        $pending = New-QualityPassword
        Set-QualitySecret -Context $Context -Name 'admin-password-pending' -Value $pending
    }
    if (-not (Test-QualityCredential -User 'admin' -Password 'admin')) {
        throw 'Fresh-stack recovery could not authenticate with either the pending or default admin password. Preserve the owned volume and inspect its scoped logs.'
    }
    $headers = Get-QualityApiHeaders -User 'admin' -Password 'admin'
    $null = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Method POST -Path 'api/users/change_password' `
        -Headers $headers -Form @{ login = 'admin'; previousPassword = 'admin'; password = $pending } `
        -RedactValues @('admin', $pending)
    if (-not (Test-QualityCredential -User 'admin' -Password $pending)) {
        throw 'The server did not accept the pending admin password after rotation; the encrypted recovery journal was retained.'
    }
    Promote-QualitySecret -PendingName 'admin-password-pending' -ConfirmedName 'admin-password' -Value $pending
    Remove-QualityFreshMarker
}

function Get-QualityProjectKey {
    param([Parameter(Mandatory)][ValidateSet('BlazorAuto', 'React')][string]$Profile, [string]$Sha)
    $mainKey = [string]$Context.ProjectKeys.$Profile
    if (-not $Sha) { return $mainKey }
    if ($Sha -notmatch '^[0-9a-f]{40}$') { throw 'Candidate SHA must be a full lowercase Git commit SHA.' }
    return "$mainKey-candidate-$($Sha.Substring(0, 12))"
}

function Ensure-QualityGroup {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Description)
    $groups = [Collections.Generic.List[object]]::new()
    $page = 1
    $total = $null
    do {
        $search = Invoke-QualityAdminApi -Path 'api/user_groups/search' -Query @{ q = $Name; p = $page; ps = 100 }
        if ($null -eq $total) { $total = [int]$search.paging.total }
        foreach ($group in @($search.groups)) { $groups.Add($group) }
        $page++
    } while ($groups.Count -lt $total)
    if ($groups.Count -ne $total) { throw "Could not enumerate all SonarQube groups matching '$Name'." }
    $existing = @($groups | Where-Object { $_.name -eq $Name }) | Select-Object -First 1
    if ($null -eq $existing) {
        $null = Invoke-QualityAdminApi -Path 'api/user_groups/create' -Method POST `
            -Form @{ name = $Name; description = $Description }
    }
}

function Get-QualityGroupsWithPermissions {
    param([string]$ProjectKey)
    $groups = [Collections.Generic.List[object]]::new()
    $page = 1
    $total = $null
    do {
        $query = @{ p = $page; ps = 100 }
        if ($ProjectKey) { $query.projectKey = $ProjectKey }
        $response = Invoke-QualityAdminApi -Path 'api/permissions/groups' -Query $query
        if ($null -eq $total) { $total = [int]$response.paging.total }
        foreach ($group in @($response.groups)) { $groups.Add($group) }
        $page++
    } while ($groups.Count -lt $total)
    if ($groups.Count -ne $total) { throw 'Could not enumerate every group permission.' }
    return @($groups)
}

function Get-QualityGroupPermissions {
    param([Parameter(Mandatory)][string]$GroupName, [string]$ProjectKey)
    $groups = @(Get-QualityGroupsWithPermissions -ProjectKey $ProjectKey)
    $group = @($groups | Where-Object { $_.name -eq $GroupName }) | Select-Object -First 1
    if ($null -eq $group) { return @() }
    return @($group.permissions | ForEach-Object { [string]$_ } | Sort-Object -Unique)
}

function Remove-QualityGroupPermission {
    param([Parameter(Mandatory)][string]$GroupName, [Parameter(Mandatory)][string]$Permission, [string]$ProjectKey)
    $form = @{ groupName = $GroupName; permission = $Permission }
    if ($ProjectKey) { $form.projectKey = $ProjectKey }
    $null = Invoke-QualityAdminApi -Path 'api/permissions/remove_group' -Method POST -Form $form
}

function Ensure-QualityNoBroadPermissions {
    $globalPermissions = @(Get-QualityGroupPermissions -GroupName 'sonar-users')
    foreach ($permission in $globalPermissions) {
        if ($permission -ne 'user') {
            Remove-QualityGroupPermission -GroupName 'sonar-users' -Permission $permission
        }
    }
    $remaining = @(Get-QualityGroupPermissions -GroupName 'sonar-users' | Where-Object { $_ -ne 'user' })
    if ($remaining.Count -gt 0) { throw "Broad global permissions remain on sonar-users: $($remaining -join ', ')." }
    $anonymousPermissions = @(Get-QualityGroupPermissions -GroupName 'anyone')
    if ($anonymousPermissions.Count -gt 0) {
        throw "The anonymous 'anyone' group has global permissions: $($anonymousPermissions -join ', ')."
    }
}

function Get-QualityReaderGroups {
    param([Parameter(Mandatory)][string]$Login)

    $groups = [Collections.Generic.List[object]]::new()
    $page = 1
    $total = $null
    do {
        $response = Invoke-QualityAdminApi -Path 'api/users/groups' -Query @{ login = $Login; p = $page; ps = 100 }
        if ($null -eq $total) { $total = [int]$response.paging.total }
        foreach ($group in @($response.groups)) { $groups.Add($group) }
        $page++
    } while ($groups.Count -lt $total)
    if ($groups.Count -ne $total) { throw "Could not enumerate every group membership for reader '$Login'." }
    return @($groups | ForEach-Object { [string]$_.name } | Sort-Object -Unique)
}

function Get-QualityDirectUserPermissions {
    param([Parameter(Mandatory)][string]$Login, [string]$ProjectKey)

    $users = [Collections.Generic.List[object]]::new()
    $page = 1
    $total = $null
    do {
        $query = @{ p = $page; ps = 100 }
        if ($ProjectKey) { $query.projectKey = $ProjectKey }
        $response = Invoke-QualityAdminApi -Path 'api/permissions/users' -Query $query
        if ($null -eq $total) { $total = [int]$response.paging.total }
        foreach ($entry in @($response.users)) { $users.Add($entry) }
        $page++
    } while ($users.Count -lt $total)
    if ($users.Count -ne $total) { throw 'Could not enumerate every direct user permission while validating a quality reader.' }
    $user = @($users | Where-Object { $_.login -eq $Login }) | Select-Object -First 1
    if ($null -eq $user) { return @() }
    return @($user.permissions | ForEach-Object { [string]$_ } | Sort-Object -Unique)
}

function Ensure-QualityProject {
    param([Parameter(Mandatory)][ValidateSet('BlazorAuto', 'React')][string]$Profile, [string]$Sha)
    $projectKey = Get-QualityProjectKey -Profile $Profile -Sha $Sha
    $found = Invoke-QualityAdminApi -Path 'api/projects/search' -Query @{ projects = $projectKey; ps = 100 }
    $project = @($found.components | Where-Object { $_.key -eq $projectKey }) | Select-Object -First 1
    if ($null -eq $project) {
        $null = Invoke-QualityAdminApi -Path 'api/projects/create' -Method POST -Form @{
            project = $projectKey
            name = "$($Context.RepositorySlug) $Profile$(if ($Sha) { " candidate $($Sha.Substring(0, 12))" })"
            visibility = 'private'
            mainBranch = 'main'
        }
    }
    $null = Invoke-QualityAdminApi -Path 'api/projects/update_visibility' -Method POST `
        -Form @{ project = $projectKey; visibility = 'private' }
    $null = Invoke-QualityAdminApi -Path 'api/new_code_periods/set' -Method POST `
        -Form @{ project = $projectKey; type = 'PREVIOUS_VERSION' }

    $groupName = "quality-reader-$($Profile.ToLowerInvariant())-$($Context.IdentityHash8)"
    Ensure-QualityGroup -Name $groupName -Description "Read-only $Profile access for $($Context.RepositoryIdentity)."
    $projectPermissions = @(Get-QualityGroupPermissions -GroupName 'sonar-users' -ProjectKey $projectKey)
    foreach ($permission in $projectPermissions) {
        Remove-QualityGroupPermission -GroupName 'sonar-users' -Permission $permission -ProjectKey $projectKey
    }
    foreach ($permission in @('user', 'codeviewer')) {
        $null = Invoke-QualityAdminApi -Path 'api/permissions/add_group' -Method POST `
            -Form @{ projectKey = $projectKey; groupName = $groupName; permission = $permission }
    }
    $adminPermissions = @(Get-QualityGroupPermissions -GroupName 'sonar-administrators' -ProjectKey $projectKey)
    if ('scan' -notin $adminPermissions) {
        $null = Invoke-QualityAdminApi -Path 'api/permissions/add_group' -Method POST `
            -Form @{ projectKey = $projectKey; groupName = 'sonar-administrators'; permission = 'scan' }
    }
    $effectiveGroups = [pscustomobject]@{ groups = @(Get-QualityGroupsWithPermissions -ProjectKey $projectKey) }
    $unexpectedGroups = @($effectiveGroups.groups | Where-Object {
        $permissions = @($_.permissions | ForEach-Object { [string]$_ })
        $isExpectedAdministrator = $_.name -eq 'sonar-administrators' -and
            $permissions.Count -eq 2 -and 'admin' -in $permissions -and 'scan' -in $permissions
        $_.name -ne $groupName -and -not $isExpectedAdministrator -and $permissions.Count -gt 0
    } | ForEach-Object { [string]$_.name })
    if ($unexpectedGroups.Count -gt 0) {
        throw "Project '$projectKey' grants permissions to unexpected groups: $($unexpectedGroups -join ', ')."
    }
    $assigned = @($effectiveGroups.groups | Where-Object { $_.name -eq $groupName } | ForEach-Object { $_.permissions })
    if ((Compare-Object -ReferenceObject @('codeviewer', 'user') -DifferenceObject $assigned)) {
        throw "Reader group '$groupName' does not have exactly Browse and See Source Code on '$projectKey'."
    }
    return [pscustomobject]@{ ProjectKey = $projectKey; ReaderGroup = $groupName; Profile = $Profile }
}

function Test-QualityUserExists {
    param([Parameter(Mandatory)][string]$Login)
    $users = [Collections.Generic.List[object]]::new()
    $page = 1
    $total = $null
    do {
        $result = Invoke-QualityAdminApi -Path 'api/users/search' -Query @{ q = $Login; p = $page; ps = 100 }
        if ($null -eq $total) { $total = [int]$result.paging.total }
        foreach ($user in @($result.users)) { $users.Add($user) }
        $page++
    } while ($users.Count -lt $total)
    if ($users.Count -ne $total) { throw "Could not enumerate every SonarQube user matching '$Login'." }
    return @($users | Where-Object { $_.login -eq $Login }).Count -gt 0
}

function Ensure-QualityReader {
    param([Parameter(Mandatory)][string]$Profile, [Parameter(Mandatory)][string]$GroupName,
        [Parameter(Mandatory)][string]$ProjectKey)
    $login = "quality-reader-$($Profile.ToLowerInvariant())-$($Context.IdentityHash8)"
    $confirmedName = "reader-$($Profile.ToLowerInvariant())-password"
    $pendingName = "reader-$($Profile.ToLowerInvariant())-password-pending"
    $confirmed = Get-QualitySecret -Context $Context -Name $confirmedName -Optional
    $pending = Get-QualitySecret -Context $Context -Name $pendingName -Optional
    $exists = Test-QualityUserExists -Login $login

    if ($confirmed -and (Test-QualityCredential -User $login -Password $confirmed)) {
        if ($pending) { Remove-QualitySecret -Context $Context -Name $pendingName }
    }
    elseif ($pending -and (Test-QualityCredential -User $login -Password $pending)) {
        Promote-QualitySecret -PendingName $pendingName -ConfirmedName $confirmedName -Value $pending
        $confirmed = $pending
    }
    else {
        if ($exists -and -not $pending) {
            throw "Owned reader '$login' exists but has no encrypted recovery password. Refusing to reset the existing account."
        }
        if (-not $pending) {
            $pending = New-QualityPassword
            Set-QualitySecret -Context $Context -Name $pendingName -Value $pending
        }
        if (-not $exists) {
            try {
                $null = Invoke-QualityAdminApi -Path 'api/v2/users-management/users' -Method POST -Json @{
                    login = $login
                    name = "$Profile read-only quality viewer"
                    password = $pending
                    local = $true
                }
            }
            catch {
                if (-not (Test-QualityUserExists -Login $login)) { throw }
            }
        }
        if (-not (Test-QualityCredential -User $login -Password $pending)) {
            throw "Reader '$login' could not authenticate with its encrypted pending password; no password reset was attempted."
        }
        Promote-QualitySecret -PendingName $pendingName -ConfirmedName $confirmedName -Value $pending
        $confirmed = $pending
    }

    $null = Invoke-QualityAdminApi -Path 'api/user_groups/add_user' -Method POST `
        -Form @{ name = $GroupName; login = $login }
    $memberships = @(Get-QualityReaderGroups -Login $login)
    $expectedMemberships = @('sonar-users', $GroupName) | Sort-Object -Unique
    if (Compare-Object -ReferenceObject $expectedMemberships -DifferenceObject $memberships) {
        throw "Reader '$login' belongs to unexpected groups: $($memberships -join ', '). Expected only sonar-users and $GroupName."
    }
    $readerGlobalPermissions = @(Get-QualityGroupPermissions -GroupName $GroupName)
    if ($readerGlobalPermissions.Count -gt 0) {
        throw "Reader group '$GroupName' has global permissions: $($readerGlobalPermissions -join ', ')."
    }
    $baseGlobalPermissions = @(Get-QualityGroupPermissions -GroupName 'sonar-users')
    if ($baseGlobalPermissions | Where-Object { $_ -ne 'user' }) {
        throw "Reader '$login' inherits broad global permissions from sonar-users."
    }
    $directGlobal = @(Get-QualityDirectUserPermissions -Login $login)
    if ($directGlobal.Count -gt 0) { throw "Reader '$login' has direct global permissions: $($directGlobal -join ', ')." }
    $directProject = @(Get-QualityDirectUserPermissions -Login $login -ProjectKey $ProjectKey)
    if ($directProject.Count -gt 0) { throw "Reader '$login' has direct project permissions on '$ProjectKey': $($directProject -join ', ')." }
    return $login
}

function Get-QualityOwnedTokens {
    param([Parameter(Mandatory)][string]$Login)
    $result = Invoke-QualityAdminApi -Path 'api/user_tokens/search' -Query @{ login = $Login }
    return @($result.userTokens)
}

function Revoke-QualityOwnedToken {
    param([Parameter(Mandatory)][string]$Login, [Parameter(Mandatory)][string]$Name)
    $null = Invoke-QualityAdminApi -Path 'api/user_tokens/revoke' -Method POST -Form @{ login = $Login; name = $Name }
}

function Ensure-QualityProjectToken {
    param([Parameter(Mandatory)][string]$Profile, [Parameter(Mandatory)][string]$ProjectKey, [string]$Sha)
    $suffix = if ($Sha) { "candidate-$($Sha.Substring(0, 12))" } else { 'main' }
    $secretName = "analysis-$($Profile.ToLowerInvariant())-$suffix"
    $tokenName = "quality-$($Context.IdentityHash8)-$($Profile.ToLowerInvariant())-$suffix"
    $token = Get-QualitySecret -Context $Context -Name $secretName -Optional
    if ($token) {
        try {
            $headers = Get-QualityApiHeaders -Token $token
            $valid = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/authentication/validate' `
                -Headers $headers -RedactValues @($token)
            if ($valid.valid -eq $true) { return $token }
        }
        catch { }
    }
    $owned = @(Get-QualityOwnedTokens -Login 'admin' | Where-Object { $_.name -eq $tokenName })
    foreach ($existing in $owned) {
        if ($existing.projectKey -and $existing.projectKey -ne $ProjectKey) {
            throw "Owned token name '$tokenName' is attached to an unexpected project; preserve it and inspect the repository namespace."
        }
        Revoke-QualityOwnedToken -Login 'admin' -Name $tokenName
    }
    $created = Invoke-QualityAdminApi -Path 'api/user_tokens/generate' -Method POST -Form @{
        name = $tokenName
        type = 'PROJECT_ANALYSIS_TOKEN'
        projectKey = $ProjectKey
    }
    if ([string]::IsNullOrWhiteSpace([string]$created.token)) { throw "SonarQube did not return the $Profile project token value." }
    Set-QualitySecret -Context $Context -Name $secretName -Value ([string]$created.token)
    return [string]$created.token
}

function Ensure-QualityReaderToken {
    param([Parameter(Mandatory)][string]$Profile, [Parameter(Mandatory)][string]$Login)
    $secretName = "reader-$($Profile.ToLowerInvariant())-token"
    $tokenName = "quality-$($Context.IdentityHash8)-$($Profile.ToLowerInvariant())-reader"
    $token = Get-QualitySecret -Context $Context -Name $secretName -Optional
    if ($token) {
        try {
            $headers = Get-QualityApiHeaders -Token $token
            $valid = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/authentication/validate' `
                -Headers $headers -RedactValues @($token)
            if ($valid.valid -eq $true) { return $token }
        }
        catch { }
    }
    $owned = @(Get-QualityOwnedTokens -Login $Login | Where-Object { $_.name -eq $tokenName })
    foreach ($existing in $owned) { Revoke-QualityOwnedToken -Login $Login -Name $tokenName }
    $created = Invoke-QualityAdminApi -Path 'api/user_tokens/generate' -Method POST -Form @{
        login = $Login
        name = $tokenName
        type = 'USER_TOKEN'
    }
    if ([string]::IsNullOrWhiteSpace([string]$created.token)) { throw "SonarQube did not return the $Profile reader token value." }
    Set-QualitySecret -Context $Context -Name $secretName -Value ([string]$created.token)
    return [string]$created.token
}

function Ensure-QualityProjectResources {
    param([Parameter(Mandatory)][string]$Profile, [string]$Sha)
    $project = Ensure-QualityProject -Profile $Profile -Sha $Sha
    $login = Ensure-QualityReader -Profile $Profile -GroupName $project.ReaderGroup -ProjectKey $project.ProjectKey
    $analysisToken = Ensure-QualityProjectToken -Profile $Profile -ProjectKey $project.ProjectKey -Sha $Sha
    $readerToken = Ensure-QualityReaderToken -Profile $Profile -Login $login
    $readerHeaders = Get-QualityApiHeaders -Token $readerToken
    $null = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/issues/search' `
        -Query @{ componentKeys = $project.ProjectKey; ps = 1 } -Headers $readerHeaders -RedactValues @($readerToken)
    $check = Invoke-QualityApi -BaseUrl $Context.BaseUrl -Path 'api/authentication/validate' `
        -Headers (Get-QualityApiHeaders -Token $analysisToken) -RedactValues @($analysisToken)
    if ($check.valid -ne $true) { throw "The $Profile project analysis token failed authentication." }
    Write-Host "Provisioned $Profile project '$($project.ProjectKey)' with private visibility and a profile-scoped reader."
}

function Apply-QualityProfileOverrides {
    $path = Join-Path $repoRoot 'Scripts/Quality/SonarQube/profile-overrides.json'
    $config = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($config.schema -ne 'blazorautoapp.sonar-profile-overrides/1') { throw 'Unsupported profile override schema.' }
    foreach ($profile in $config.profiles) {
        foreach ($entry in $profile.deactivate) {
            if ([string]::IsNullOrWhiteSpace([string]$entry.reason)) { throw "Rule '$($entry.rule)' has no reviewed reason." }
        }
    }
    if (@($config.profiles).Count -gt 0) {
        throw 'Reviewed rule overrides require explicit implementation and server acceptance; the current accepted default keeps overrides empty.'
    }
    Write-Host 'Quality profile overrides are empty; inherited Sonar defaults remain active.'
}

try {
    New-Item -ItemType Directory -Force -Path $Context.BaseDirectory | Out-Null
    if ($Start) {
        Test-QualityDockerLinux
        $port = Resolve-QualityHostPort -Context $Context
        Save-QualityPrivateSettings -Context $Context
        $databasePassword = Ensure-QualityDatabasePassword
        Assert-QualityPortOwnership -DatabasePassword $databasePassword
        $null = Invoke-QualityCompose -Arguments @('up', '-d') -DatabasePassword $databasePassword -StepName 'compose-up'
        Wait-QualityServer -Context $Context -TimeoutSeconds 600
        Write-Host "SonarQube is ready at $($Context.BaseUrl)."

        if ($Initialize) {
            Ensure-QualityAdminPassword
            Ensure-QualityNoBroadPermissions
            foreach ($profile in @('BlazorAuto', 'React')) { Ensure-QualityProjectResources -Profile $profile }
            Apply-QualityProfileOverrides
            Write-Host "Owned SonarQube projects are ready: $($Context.ProjectKeys.BlazorAuto), $($Context.ProjectKeys.React)."
        }
        elseif ($ApplyProfile) {
            Ensure-QualityAdminPassword
            Apply-QualityProfileOverrides
        }
        elseif ($EnsureCandidate) {
            Ensure-QualityAdminPassword
            Ensure-QualityNoBroadPermissions
            Ensure-QualityProjectResources -Profile $FrontendProfile -Sha $CandidateSha
        }
    }
    elseif ($Stop) {
        $databasePassword = Get-QualitySecret -Context $Context -Name 'database-password' -Optional
        $null = Invoke-QualityCompose -Arguments @('stop') -DatabasePassword $databasePassword -StepName 'compose-stop'
        Write-Host 'Owned SonarQube services stopped. Named history volumes remain in place.'
    }
    elseif ($Status) {
        $databasePassword = Get-QualitySecret -Context $Context -Name 'database-password' -Optional
        $result = Invoke-QualityCompose -Arguments @('ps', '--all') -DatabasePassword $databasePassword -StepName 'compose-status'
        if (-not [string]::IsNullOrWhiteSpace($result.Stdout)) { Write-Host $result.Stdout.TrimEnd() }
        try { $state = (Invoke-RestMethod -Uri "$($Context.BaseUrl)/api/system/status" -TimeoutSec 5).status }
        catch { $state = 'unreachable' }
        Write-Host "SonarQube API: $state ($($Context.BaseUrl))"
        foreach ($name in @('database-password', 'admin-password', 'analysis-blazorauto-main', 'analysis-react-main', 'reader-blazorauto-token', 'reader-react-token')) {
            Write-Host ("{0}: {1}" -f $name, $(if (Test-QualitySecret -Context $Context -Name $name) { 'present' } else { 'missing' }))
        }
    }
    elseif ($Logs) {
        $databasePassword = Get-QualitySecret -Context $Context -Name 'database-password' -Optional
        $result = Invoke-QualityCompose -Arguments @('logs', '--tail', '200', 'sonarqube', 'database') `
            -DatabasePassword $databasePassword -StepName 'compose-logs'
        if (-not [string]::IsNullOrWhiteSpace($result.Stdout)) { Write-Host $result.Stdout.TrimEnd() }
    }
}
finally {
    if ($ownsLock -and $lock) { Exit-QualityLock -Lock $lock }
}
