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
    $profileDataDir = Get-ProfileDataDir -PathConfig $pathConfig -Profile $Profile
    $pythonExe = Get-PythonExePath -PathConfig $pathConfig

    Assert-DirectoryExists -Path $pathConfig.AppDir -Label "Diretorio do app"
    Assert-NonEmptyFile -Path $catalogPath -Label "Catalogo do profile"
    Assert-FileExists -Path $pythonExe -Label "Python da venv"

    New-Item -ItemType Directory -Force -Path $profileDataDir | Out-Null

    Write-InfoLine "Iniciando wrapper de prepare"
    Write-InfoLine "profile=$Profile"
    Write-InfoLine "app_dir=$($pathConfig.AppDir)"
    Write-InfoLine "catalog_path=$catalogPath"
    Write-InfoLine "data_dir=$profileDataDir"

    Push-Location $pathConfig.AppDir
    try {
        & $pythonExe `
            -m ofertas_bot.local_flow_cli `
            --stage prepare `
            --profile $Profile `
            --data-dir $profileDataDir `
            --catalog-file $catalogPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        throw "Prepare retornou exit code $exitCode"
    }

    Write-InfoLine "Prepare concluido"
    Write-Output "PROFILE_DATA_DIR=$profileDataDir"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique app, catalogo e ambiente antes de reexecutar o prepare."
    exit 1
}

