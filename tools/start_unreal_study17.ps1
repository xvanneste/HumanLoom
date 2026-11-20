$ErrorActionPreference='Stop'
$studyProject=(Resolve-Path (Join-Path $PSScriptRoot '../unreal/HumanReferenceStudy/HumanReferenceStudy.uproject')).Path
$studyRoot=Split-Path $studyProject
$studyEngine='G:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
if (-not (Test-Path -LiteralPath $studyEngine)) { throw 'Unreal 5.8 executable is missing at the recorded installation path.' }
$studyPidFile=Join-Path $studyRoot 'Saved/ReferenceStudy-MCP.pid'
if (Test-Path -LiteralPath $studyPidFile) {
    $studyExisting=Get-Process -Id ([int](Get-Content -LiteralPath $studyPidFile)) -ErrorAction SilentlyContinue
    if ($studyExisting -and $studyExisting.ProcessName -eq 'UnrealEditor') { $studyExisting | Select-Object Id; exit 0 }
}
$studyProc=Start-Process -FilePath $studyEngine -ArgumentList @(
    ('"'+$studyProject+'"'),'-NullRHI','-nosound','-unattended','-nosplash','-ModelContextProtocolStartServer',
    ('-LocalDataCachePath="'+(Join-Path $studyRoot 'DerivedDataCache')+'"'),
    ('-abslog="'+(Join-Path $studyRoot 'Saved/Logs/ReferenceStudy-MCP.log')+'"')
) -WindowStyle Hidden -PassThru
$studyProc.Id | Set-Content -LiteralPath $studyPidFile
$studyProc | Select-Object Id
