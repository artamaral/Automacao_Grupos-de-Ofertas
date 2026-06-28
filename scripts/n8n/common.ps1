Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:AllowedProfiles = @("feminino", "mae-e-bebe", "auto-e-moto")

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

