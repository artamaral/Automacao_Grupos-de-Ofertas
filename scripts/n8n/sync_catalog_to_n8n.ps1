param(
    [Parameter(Mandatory = $true)]
    [string]$Profile,
    [string]$SourceCatalogPath = "",
    [string]$RootDir = "",
    [string]$AppDir = "",
    [string]$CatalogsDir = "",
    [string]$DataDir = "",
    [string]$OperatorName = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

try {
    Assert-AllowedProfile -Profile $Profile
    $pathConfig = Get-N8nPathConfig -RootDir $RootDir -AppDir $AppDir -CatalogsDir $CatalogsDir -DataDir $DataDir
    $registryEntry = Get-CatalogRegistryEntry -PathConfig $pathConfig -Profile $Profile
    $resolvedSourceCatalogPath = $SourceCatalogPath
    $sourceMode = "manual"
    if ([string]::IsNullOrWhiteSpace($resolvedSourceCatalogPath)) {
        $resolvedSourceCatalogPath = Get-DefaultSourceCatalogPath -PathConfig $pathConfig -Profile $Profile
        $sourceMode = "default"
    }

    Assert-NonEmptyFile -Path $resolvedSourceCatalogPath -Label "Catalogo de origem"

    $targetPath = Get-ProfileCatalogPath -PathConfig $pathConfig -Profile $Profile
    $targetDir = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Copy-Item -LiteralPath $resolvedSourceCatalogPath -Destination $targetPath -Force

    $metadataPath = Join-Path $targetDir "catalog_sync_metadata.json"
    $operator = $OperatorName
    if ([string]::IsNullOrWhiteSpace($operator)) {
        $operator = $env:USERNAME
    }

    Save-JsonFile -Path $metadataPath -Payload @{
        profile = $Profile
        source_catalog_path = $resolvedSourceCatalogPath
        source_mode = $sourceMode
        target_catalog_path = $targetPath
        synced_at = (Get-Date).ToString("o")
        operator = $operator
        drive_file_id = if ($null -ne $registryEntry) { $registryEntry.drive_file_id } else { "" }
        drive_url = if ($null -ne $registryEntry) { $registryEntry.drive_url } else { "" }
    }

    Write-InfoLine "Catalogo sincronizado para o ambiente do n8n"
    Write-InfoLine "profile=$Profile"
    Write-InfoLine "source=$resolvedSourceCatalogPath"
    Write-InfoLine "source_mode=$sourceMode"
    Write-InfoLine "target=$targetPath"
    Write-InfoLine "metadata=$metadataPath"
    Write-Output "CATALOG_SYNC_OK=$targetPath"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique profile, catalogo de origem e paths do n8n antes de repetir a sincronizacao."
    exit 1
}
