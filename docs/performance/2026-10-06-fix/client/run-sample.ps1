param([string]$Label='before',[double]$Rate=1,[switch]$FollowPeers,[int]$Width=1280,[int]$Height=720,[double]$Zoom=0)
$ErrorActionPreference='Stop'
$extra=if($FollowPeers){',followPeers:true,peerCounts:[29]'}else{''}
$options = 'window.__sampleOptions = {label:' + "'$Label'" + ',rate:' + $Rate + ',width:' + $Width + ',height:' + $Height + ',zoom:' + $Zoom + $extra + '}'
npx --yes --package '@playwright/cli' playwright-cli '-s=frame-diagnosis' eval $options | Out-Null
$result = npx --yes --package '@playwright/cli' playwright-cli '-s=frame-diagnosis' run-code --filename 'output/client-perf-20261006/sample.cjs'
$raw = $result -join "`n"
$raw | Set-Content -LiteralPath "output/client-perf-20261006/$Label-$($Rate)x.log" -Encoding utf8
if($raw -notmatch '(?s)### Result\s*(\{.*?\})\s*### Ran') { throw $raw }
$json = $Matches[1]
$json | Set-Content -LiteralPath "output/client-perf-20261006/$Label-$($Rate)x.json" -Encoding utf8
$parsed = $json | ConvertFrom-Json
$parsed.results | Select-Object peerCount,rate,frames,over25ms,over50ms,costs,metrics,actorReused,end | ConvertTo-Json -Depth 8
