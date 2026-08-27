[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$deployRoot = Join-Path $repositoryRoot 'deploy'
$publicHtml = Join-Path $deployRoot 'public_html'
$archivePath = Join-Path $deployRoot 'landing-feminino-public-html.zip'

$requiredFiles = @(
    '.htaccess',
    '_config/whatsapp.php',
    'feminino/index.html',
    'assets/css/feminino.css',
    'assets/js/feminino.js',
    'assets/qr/whatsapp-feminino.png',
    'go/whatsapp/feminino/index.php',
    'error/whatsapp-indisponivel.html'
)

foreach ($relativePath in $requiredFiles) {
    $absolutePath = Join-Path $publicHtml $relativePath
    if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
        throw "Arquivo de produção ausente: $relativePath"
    }
}

$forbiddenNames = @('.git', 'docs', 'tests', 'node_modules', '.env')
$forbidden = Get-ChildItem -LiteralPath $publicHtml -Recurse -Force | Where-Object {
    $forbiddenNames -contains $_.Name
}
if ($forbidden) {
    throw "Conteúdo proibido no pacote: $($forbidden.FullName -join ', ')"
}

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$archiveStream = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::CreateNew)
try {
    $archive = [System.IO.Compression.ZipArchive]::new(
        $archiveStream,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )
    try {
        Get-ChildItem -LiteralPath $publicHtml -Recurse -Force -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($publicHtml.Length).TrimStart('\', '/')
            $entryName = 'public_html/' + $relativePath.Replace('\', '/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $_.FullName,
                $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    } finally {
        $archive.Dispose()
    }
} finally {
    $archiveStream.Dispose()
}

Write-Output "Pacote criado: $archivePath"
