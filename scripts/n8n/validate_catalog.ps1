param(
    [Parameter(Mandatory = $true)]
    [string]$Profile,
    [string]$RootDir = "",
    [string]$AppDir = "",
    [string]$CatalogsDir = "",
    [string]$DataDir = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

try {
    Assert-AllowedProfile -Profile $Profile
    $pathConfig = Get-N8nPathConfig -RootDir $RootDir -AppDir $AppDir -CatalogsDir $CatalogsDir -DataDir $DataDir
    $catalogPath = Get-ProfileCatalogPath -PathConfig $pathConfig -Profile $Profile

    Write-InfoLine "Validando catalogo ativo"
    Write-InfoLine "profile=$Profile"
    Write-InfoLine "catalog_path=$catalogPath"

    Assert-NonEmptyFile -Path $catalogPath -Label "Catalogo do profile"

    Write-InfoLine "Catalogo valido"
    Write-Output "CATALOG_OK=$catalogPath"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Atualize o catalogo ativo do profile no ambiente do n8n antes de seguir."
    exit 1
}

