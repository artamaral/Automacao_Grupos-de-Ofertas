param(
    [string]$Profile = "",
    [string]$ProfilesCsv = "",
    [string]$ProfilesFile = "",
    [string]$RootDir = "",
    [string]$AppDir = "",
    [string]$CatalogsDir = "",
    [string]$DataDir = "",
    [string]$RunId = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

try {
    $pathConfig = Get-N8nPathConfig -RootDir $RootDir -AppDir $AppDir -CatalogsDir $CatalogsDir -DataDir $DataDir
    $profiles = Get-ProfilesFromInput -Profile $Profile -ProfilesCsv $ProfilesCsv -ProfilesFile $ProfilesFile
    if ([string]::IsNullOrWhiteSpace($RunId)) {
        $RunId = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ss")
    }

    $results = New-Object System.Collections.Generic.List[object]
    foreach ($currentProfile in $profiles) {
        $wrapperPath = Join-Path $scriptDir "invoke_prepare.ps1"
        Write-InfoLine "Janela prepare: iniciando profile=$currentProfile"
        & powershell -ExecutionPolicy Bypass -File $wrapperPath `
            -Profile $currentProfile `
            -RootDir $pathConfig.RootDir `
            -AppDir $pathConfig.AppDir `
            -CatalogsDir $pathConfig.CatalogsDir `
            -DataDir $pathConfig.DataDir
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Prepare da janela falhou para profile=$currentProfile com exit code $exitCode"
        }
        $results.Add(
            @{
                profile = $currentProfile
                data_dir = (Get-ProfileDataDir -PathConfig $pathConfig -Profile $currentProfile)
                catalog_path = (Get-ProfileCatalogPath -PathConfig $pathConfig -Profile $currentProfile)
                status = "ok"
            }
        )
    }

    $summaryPath = Join-Path $pathConfig.DataDir ("window_prepare_summary_" + $RunId + ".json")
    Save-JsonFile -Path $summaryPath -Payload @{
        run_id = $RunId
        profiles = $results
        total_profiles = $results.Count
        stage = "prepare"
    }

    Write-InfoLine "Janela prepare concluida"
    Write-InfoLine "run_id=$RunId"
    Write-InfoLine "total_profiles=$($results.Count)"
    Write-Output "WINDOW_PREPARE_SUMMARY=$summaryPath"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique profiles, catalogos e ambiente antes de reexecutar a janela de prepare."
    exit 1
}
