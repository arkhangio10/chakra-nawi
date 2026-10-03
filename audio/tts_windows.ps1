<#
Audios PROVISIONALES en castellano con la voz TTS de Windows (System.Speech). Son SINTETICOS.
Lo llama audio/tts_provisional.py; no hace falta correrlo a mano.

  powershell -NoProfile -ExecutionPolicy Bypass -File audio/tts_windows.ps1 -Textos textos.json -Salida carpeta

textos.json (UTF-8): { "CODIGO": "texto", ... }  ->  carpeta/CODIGO.wav (22,05 kHz, 16 bits, mono)
Usa la primera voz instalada cuya cultura empiece por -Cultura (por defecto "es"). Si no hay, sale con codigo 3.
Este archivo se mantiene en ASCII: PowerShell 5.1 lee los .ps1 sin BOM como ANSI.
#>
param(
    [Parameter(Mandatory = $true)][string]$Textos,
    [Parameter(Mandatory = $true)][string]$Salida,
    [int]$Velocidad = -1,
    [string]$Cultura = 'es'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$sintetizador = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voz = $sintetizador.GetInstalledVoices() |
    Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like "$Cultura*" } |
    Select-Object -First 1
if (-not $voz) {
    $hay = ($sintetizador.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name + ' (' + $_.VoiceInfo.Culture.Name + ')' }) -join ', '
    [Console]::Error.WriteLine("No hay una voz TTS '$Cultura' instalada. Voces disponibles: $hay. " +
        "Instalar en Configuracion > Hora e idioma > Voz > Agregar voces.")
    exit 3
}
$sintetizador.SelectVoice($voz.VoiceInfo.Name)
$sintetizador.Rate = $Velocidad
$formato = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050,
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
New-Item -ItemType Directory -Force -Path $Salida | Out-Null
$datos = Get-Content -Raw -Encoding UTF8 -Path $Textos | ConvertFrom-Json
foreach ($p in $datos.PSObject.Properties) {
    $sintetizador.SetOutputToWaveFile((Join-Path $Salida ($p.Name + '.wav')), $formato)
    $sintetizador.Speak([string]$p.Value)
    $sintetizador.SetOutputToNull()
}
$sintetizador.Dispose()
Write-Output ('VOZ=' + $voz.VoiceInfo.Name + '|' + $voz.VoiceInfo.Culture.Name)
