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
    $profileDataDir = Get-ProfileDataDir -PathConfig $pathConfig -Profile $Profile
    $pythonExe = Get-PythonExePath -PathConfig $pathConfig
    $reviewQueuePath = Join-Path $profileDataDir "review_queue.json"

    Assert-DirectoryExists -Path $pathConfig.AppDir -Label "Diretorio do app"
    Assert-DirectoryExists -Path $profileDataDir -Label "Diretorio de dados do profile"
    Assert-NonEmptyFile -Path $reviewQueuePath -Label "Review queue do profile"
    Assert-FileExists -Path $pythonExe -Label "Python da venv"

    Write-InfoLine "Iniciando wrapper de finalize"
    Write-InfoLine "profile=$Profile"
    Write-InfoLine "app_dir=$($pathConfig.AppDir)"
    Write-InfoLine "data_dir=$profileDataDir"

    Push-Location $pathConfig.AppDir
    try {
        & $pythonExe `
            -m ofertas_bot.local_flow_cli `
            --stage finalize `
            --profile $Profile `
            --data-dir $profileDataDir
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        throw "Finalize retornou exit code $exitCode"
    }

    Write-InfoLine "Finalize concluido"
    Write-Output "PROFILE_DATA_DIR=$profileDataDir"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique review_queue, ambiente e artefatos antes de reexecutar o finalize."
    exit 1
}

