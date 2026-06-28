Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:AllowedProfiles = @("feminino", "mae-e-bebe", "auto-e-moto")
$script:CatalogRegistryCache = $null

function Write-InfoLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "INFO | $Message"
}

function Write-ActionLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "ACAO | $Message"
}

function Write-ErrorLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Error "ERRO | $Message"
}

function Get-N8nPathConfig {
    param(
        [string]$RootDir = "",
        [string]$AppDir = "",
        [string]$CatalogsDir = "",
        [string]$DataDir = ""
    )

    $resolvedRootDir = $RootDir
    if ([string]::IsNullOrWhiteSpace($resolvedRootDir)) {
        $resolvedRootDir = $env:N8N_OFERTAS_ROOT
    }
    if ([string]::IsNullOrWhiteSpace($resolvedRootDir)) {
        throw "N8N_OFERTAS_ROOT nao informado"
    }

    $resolvedAppDir = $AppDir
    if ([string]::IsNullOrWhiteSpace($resolvedAppDir)) {
        $resolvedAppDir = $env:N8N_OFERTAS_APP
    }
    if ([string]::IsNullOrWhiteSpace($resolvedAppDir)) {
        $resolvedAppDir = Join-Path $resolvedRootDir "app\Automacao_Grupos-de-Ofertas"
    }

    $resolvedCatalogsDir = $CatalogsDir
    if ([string]::IsNullOrWhiteSpace($resolvedCatalogsDir)) {
        $resolvedCatalogsDir = $env:N8N_OFERTAS_CATALOGS
    }
    if ([string]::IsNullOrWhiteSpace($resolvedCatalogsDir)) {
        $resolvedCatalogsDir = Join-Path $resolvedRootDir "catalogs"
    }

    $resolvedDataDir = $DataDir
    if ([string]::IsNullOrWhiteSpace($resolvedDataDir)) {
        $resolvedDataDir = $env:N8N_OFERTAS_DATA
    }
    if ([string]::IsNullOrWhiteSpace($resolvedDataDir)) {
        $resolvedDataDir = Join-Path $resolvedRootDir "data"
    }

    return @{
        RootDir = $resolvedRootDir
        AppDir = $resolvedAppDir
        CatalogsDir = $resolvedCatalogsDir
        DataDir = $resolvedDataDir
    }
}

function Assert-AllowedProfile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Profile
    )

    if ($script:AllowedProfiles -notcontains $Profile) {
        $allowed = $script:AllowedProfiles -join ", "
        throw "profile fora do contrato operacional: $Profile. Permitidos: $allowed"
    }
}

function Get-ProfileCatalogPath {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig,
        [Parameter(Mandatory = $true)]
        [string]$Profile
    )

    $registryEntry = Get-CatalogRegistryEntry -PathConfig $PathConfig -Profile $Profile
    if ($null -ne $registryEntry -and ($registryEntry.active -eq $true)) {
        return Join-Path (Join-Path $PathConfig.CatalogsDir $registryEntry.relative_dir) $registryEntry.file_name
    }

    return Join-Path (Join-Path $PathConfig.CatalogsDir $Profile) "clean_catalog_rating_4_8_plus.csv"
}

function Get-ProfileDataDir {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig,
        [Parameter(Mandatory = $true)]
        [string]$Profile
    )

    return Join-Path $PathConfig.DataDir $Profile
}

function Get-PythonExePath {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig
    )

    return Join-Path $PathConfig.AppDir ".venv\Scripts\python.exe"
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label nao encontrado em $Path"
    }
}

function Assert-DirectoryExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Label nao encontrado em $Path"
    }
}

function Assert-NonEmptyFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Assert-FileExists -Path $Path -Label $Label
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -le 0) {
        throw "$Label vazio em $Path"
    }
}

function Get-ProfilesFromInput {
    param(
        [string]$Profile = "",
        [string]$ProfilesCsv = "",
        [string]$ProfilesFile = ""
    )

    $profiles = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $profiles.Add($Profile.Trim())
    }

    if (-not [string]::IsNullOrWhiteSpace($ProfilesCsv)) {
        foreach ($item in $ProfilesCsv.Split(",")) {
            $normalized = $item.Trim()
            if (-not [string]::IsNullOrWhiteSpace($normalized)) {
                $profiles.Add($normalized)
            }
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($ProfilesFile)) {
        Assert-NonEmptyFile -Path $ProfilesFile -Label "Arquivo de profiles"
        $rawProfiles = Get-Content -LiteralPath $ProfilesFile -Encoding utf8
        foreach ($item in $rawProfiles) {
            $normalized = $item.Trim()
            if (-not [string]::IsNullOrWhiteSpace($normalized)) {
                $profiles.Add($normalized)
            }
        }
    }

    if ($profiles.Count -eq 0) {
        throw "Nenhum profile informado. Use -Profile, -ProfilesCsv ou -ProfilesFile."
    }

    $uniqueProfiles = New-Object System.Collections.Generic.List[string]
    foreach ($item in $profiles) {
        if ($uniqueProfiles -notcontains $item) {
            Assert-AllowedProfile -Profile $item
            $uniqueProfiles.Add($item)
        }
    }

    return [string[]]$uniqueProfiles
}

function Save-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Payload
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $Path -Value $json -Encoding utf8
}

function Get-CatalogRegistryPath {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig
    )

    return Join-Path $PathConfig.AppDir "n8n\google_sheets_seed\catalog_registry.csv"
}

function Get-CatalogRegistry {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig
    )

    if ($null -ne $script:CatalogRegistryCache) {
        return $script:CatalogRegistryCache
    }

    $registryPath = Get-CatalogRegistryPath -PathConfig $PathConfig
    if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) {
        $script:CatalogRegistryCache = @{}
        return $script:CatalogRegistryCache
    }

    $rows = Import-Csv -LiteralPath $registryPath
    $registry = @{}
    foreach ($row in $rows) {
        $normalizedProfile = [string]$row.profile
        if ([string]::IsNullOrWhiteSpace($normalizedProfile)) {
            continue
        }

        $normalizedProfile = $normalizedProfile.Trim().ToLowerInvariant()
        $relativeDir = [string]$row.relative_dir
        $fileName = [string]$row.file_name
        $driveFileId = [string]$row.drive_file_id
        $driveUrl = [string]$row.drive_url
        $active = $true
        $activeRaw = [string]$row.active
        if (-not [string]::IsNullOrWhiteSpace($activeRaw)) {
            $active = @("true", "1", "yes") -contains $activeRaw.Trim().ToLowerInvariant()
        }

        $registry[$normalizedProfile] = @{
            profile = $normalizedProfile
            relative_dir = $relativeDir.Trim().Replace("/", "\")
            file_name = $fileName.Trim()
            drive_file_id = $driveFileId.Trim()
            drive_url = $driveUrl.Trim()
            active = $active
        }
    }

    $script:CatalogRegistryCache = $registry
    return $script:CatalogRegistryCache
}

function Get-CatalogRegistryEntry {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig,
        [Parameter(Mandatory = $true)]
        [string]$Profile
    )

    $registry = Get-CatalogRegistry -PathConfig $PathConfig
    $normalizedProfile = $Profile.Trim().ToLowerInvariant()
    if ($registry.ContainsKey($normalizedProfile)) {
        return $registry[$normalizedProfile]
    }

    return $null
}

function Get-DefaultSourceCatalogPath {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PathConfig,
        [Parameter(Mandatory = $true)]
        [string]$Profile
    )

    $registryEntry = Get-CatalogRegistryEntry -PathConfig $PathConfig -Profile $Profile
    if ($null -ne $registryEntry -and ($registryEntry.active -eq $true)) {
        $baseDir = Join-Path (Join-Path $PathConfig.AppDir "catalogs\clean") $registryEntry.relative_dir
        return Join-Path $baseDir $registryEntry.file_name
    }

    return Join-Path (Join-Path (Join-Path $PathConfig.AppDir "catalogs\clean") $Profile) "clean_catalog_rating_4_8_plus.csv"
}
