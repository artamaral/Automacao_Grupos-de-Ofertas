param(
    [string]$Profile = "",
    [string]$ProfilesCsv = "",
    [string]$ProfilesFile = "",
    [string]$RootDir = "",
    [string]$AppDir = "",
    [string]$CatalogsDir = "",
    [string]$DataDir = "",
    [string]$RunId = "",
    [string]$OperatorName = ""
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
        $wrapperPath = Join-Path $scriptDir "sync_catalog_to_n8n.ps1"
        Write-InfoLine "Janela sync: iniciando profile=$currentProfile"
        $wrapperArgs = @(
            "-ExecutionPolicy", "Bypass",
            "-File", $wrapperPath,
            "-Profile", $currentProfile,
            "-RootDir", $pathConfig.RootDir,
            "-AppDir", $pathConfig.AppDir,
            "-CatalogsDir", $pathConfig.CatalogsDir,
            "-DataDir", $pathConfig.DataDir
        )
        if (-not [string]::IsNullOrWhiteSpace($OperatorName)) {
            $wrapperArgs += @("-OperatorName", $OperatorName)
        }
        & powershell @wrapperArgs
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Sync da janela falhou para profile=$currentProfile com exit code $exitCode"
        }

        $targetPath = Get-ProfileCatalogPath -PathConfig $pathConfig -Profile $currentProfile
        $targetDir = Split-Path -Parent $targetPath
        $metadataPath = Join-Path $targetDir "catalog_sync_metadata.json"
        $results.Add(
            @{
                profile = $currentProfile
                catalog_path = $targetPath
                metadata_path = $metadataPath
                status = "ok"
            }
        )
    }

    $summaryPath = Join-Path $pathConfig.DataDir ("window_catalog_sync_summary_" + $RunId + ".json")
    Save-JsonFile -Path $summaryPath -Payload @{
        run_id = $RunId
        profiles = $results
        total_profiles = $results.Count
        stage = "catalog_sync"
    }

    Write-InfoLine "Janela sync concluida"
    Write-InfoLine "run_id=$RunId"
    Write-InfoLine "total_profiles=$($results.Count)"
    Write-Output "WINDOW_CATALOG_SYNC_SUMMARY=$summaryPath"
    exit 0
}
catch {
    Write-ErrorLine $_.Exception.Message
    Write-ActionLine "Verifique catalogos de origem, registry e ambiente antes de reexecutar a janela de sync."
    exit 1
}
