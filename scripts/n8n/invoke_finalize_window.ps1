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
        $wrapperPath = Join-Path $scriptDir "invoke_finalize.ps1"
        Write-InfoLine "Janela finalize: iniciando profile=$currentProfile"
        & powershell -ExecutionPolicy Bypass -File $wrapperPath `
            -Profile $currentProfile `
            -RootDir $pathConfig.RootDir `
            -AppDir $pathConfig.AppDir `
            -CatalogsDir $pathConfig.CatalogsDir `
            -DataDir $pathConfig.DataDir
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Finalize da janela falhou para profile=$currentProfile com exit code $exitCode"
        }
        $results.Add(
            @{
                profile = $currentProfile
                data_dir = (Get-ProfileDataDir -PathConfig $pathConfig -Profile $currentProfile)
                dispatch_artifact = (Join-Path (Get-ProfileDataDir -PathConfig $pathConfig -Profile $currentProfile) "dispatch_artifact.json")
                dispatch_report = (Join-Path (Get-ProfileDataDir -PathConfig $pathConfig -Profile $currentProfile) "dispatch_report.json")
                status = "ok"
            }
        )
    }

    $summaryPath = Join-Path $pathConfig.DataDir ("window_finalize_summary_" + $RunId + ".json")
    Save-JsonFile -Path $summaryPath -Payload @{
        run_id = $RunId
        profiles = $results
        total_profiles = $results.Count
        stage = "finalize"
    }

    Write-InfoLine "Janela finalize concluida"
    Write-InfoLine "run_id=$RunId"
    Write-InfoLine "total_profiles=$($results.Count)"
    Write-Output "WINDOW_FINALIZE_SUMMARY=$summaryPath"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique review_queue, profiles e ambiente antes de reexecutar a janela de finalize."
    exit 1
}
