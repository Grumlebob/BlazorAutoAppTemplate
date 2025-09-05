param(
  [Parameter(Mandatory=$true)][string]$Feature
)

$ErrorActionPreference = 'Stop'

# Resolve repo root relative to this script (BlazorAutoApp.Test/tools)
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..' '..')
$coreFeatureDir = Join-Path $repoRoot "BlazorAutoApp.Core/Features/$Feature"
$testFeatureDir = Join-Path $repoRoot "BlazorAutoApp.Test/Features/$Feature"

if (-not (Test-Path $coreFeatureDir)) {
  throw "Core feature directory not found: $coreFeatureDir"
}

if (-not (Test-Path $testFeatureDir)) {
  New-Item -ItemType Directory -Path $testFeatureDir | Out-Null
}

# Find *Request classes in Core feature
$requestNames = Get-ChildItem -Path $coreFeatureDir -Filter '*.cs' -Recurse |
  Select-String -Pattern 'class\s+(\w+)Request\b' | ForEach-Object {
    $_.Matches | ForEach-Object { $_.Groups[1].Value }
  } | Sort-Object -Unique

if (-not $requestNames -or $requestNames.Count -eq 0) {
  Write-Host "No *Request classes found in $coreFeatureDir"
  exit 0
}

$created = @()
$skipped = @()

foreach ($slice in $requestNames) {
  $testFile = Join-Path $testFeatureDir ("{0}Tests.cs" -f $slice)
  if (Test-Path $testFile) {
    $skipped += (Split-Path $testFile -Leaf)
    continue
  }

  $content = @"
using System;
using Xunit;

namespace BlazorAutoApp.Test.Features.$Feature;

[Collection("MediaTestCollection")]
public class ${slice}Tests
{
    [Fact(Skip = "TODO: implement tests for $Feature/$slice")]
    public void Placeholder() => Assert.True(true);
}
"@

  Set-Content -Path $testFile -Value $content -Encoding UTF8
  $created += (Split-Path $testFile -Leaf)
}

Write-Host "Feature: $Feature"
Write-Host "Created: $($created -join ', ' )"
Write-Host "Skipped (already exist): $($skipped -join ', ' )"

