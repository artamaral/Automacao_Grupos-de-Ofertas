param(
    [Parameter(Mandatory = $true)]
    [string]$Profile,
    [Parameter(Mandatory = $true)]
    [string]$SourceCatalogPath,
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
    Assert-NonEmptyFile -Path $SourceCatalogPath -Label "Catalogo de origem"

    $targetDir = Join-Path $pathConfig.CatalogsDir $Profile
    $targetPath = Join-Path $targetDir "clean_catalog_rating_4_8_plus.csv"
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Copy-Item -LiteralPath $SourceCatalogPath -Destination $targetPath -Force

    $metadataPath = Join-Path $targetDir "catalog_sync_metadata.json"
    $operator = $OperatorName
    if ([string]::IsNullOrWhiteSpace($operator)) {
        $operator = $env:USERNAME
    }

    Save-JsonFile -Path $metadataPath -Payload @{
        profile = $Profile
        source_catalog_path = $SourceCatalogPath
        target_catalog_path = $targetPath
        synced_at = (Get-Date).ToString("o")
        operator = $operator
    }

    Write-InfoLine "Catalogo sincronizado para o ambiente do n8n"
    Write-InfoLine "profile=$Profile"
    Write-InfoLine "source=$SourceCatalogPath"
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
