param(
    [string]$Network = 'pdf-extractext-sistema_default',
    [string]$Output = "results/$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pdfs = Join-Path $root 'pdfs'
$out = Join-Path $root $Output
New-Item -ItemType Directory -Force $out | Out-Null

if (@(Get-ChildItem $pdfs -Filter *.pdf -ErrorAction SilentlyContinue).Count -ne 4) {
    throw "Copiar los 4 PDFs oficiales en $pdfs (ver load/README.md)."
}

$mounts = @('-v', "${root}:/load:ro", '-v', "${out}:/results")

docker run --rm --network $Network @mounts grafana/k6 run `
    --summary-export=/results/k6.json /load/k6-spike.js | Tee-Object "$out/k6.log"

docker run --rm --network $Network @mounts --entrypoint sh peterevans/vegeta -c `
    'vegeta attack -rate=50 -duration=30s -timeout=30s -targets=/load/vegeta-targets.txt > /results/vegeta.bin && vegeta report < /results/vegeta.bin && vegeta report -type=json < /results/vegeta.bin > /results/vegeta.json' `
    | Tee-Object "$out/vegeta.log"

docker ps --format '{{.Names}} {{.Status}}' | Out-File "$out/servicios.txt"
Write-Host "Resultados en $out"
