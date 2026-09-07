param([string]$Text, [string]$Ziel, [string]$Stimme = "Microsoft Stefan")

Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Warte($op, $typ) {
  $m = $asTask.MakeGenericMethod($typ)
  $t = $m.Invoke($null, @($op))
  $t.Wait(-1) | Out-Null
  $t.Result
}

$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$gewaehlt = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -eq $Stimme }
if ($gewaehlt) { $synth.Voice = $gewaehlt[0] }

$strom = Warte $synth.SynthesizeTextToStreamAsync($Text) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$leser = New-Object Windows.Storage.Streams.DataReader($strom.GetInputStreamAt(0))
Warte $leser.LoadAsync([uint32]$strom.Size) ([uint32]) | Out-Null
$puffer = New-Object byte[] $strom.Size
$leser.ReadBytes($puffer)
[System.IO.File]::WriteAllBytes($Ziel, $puffer)
Write-Output ("{0} : {1} Bytes" -f $Ziel, $puffer.Length)
