param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$Output,
  [string]$Browser = "C:\Program Files\Google\Chrome\Application\chrome.exe",
  [int]$Port = 9233,
  [int]$Width = 1440,
  [int]$Height = 1000,
  [string]$WaitText = "reference inspect",
  [int]$WaitTimeoutSeconds = 180,
  [int]$ExtraWaitSeconds = 2,
  [string]$ClickSelector = "",
  [int]$AfterClickWaitSeconds = 0
)

$ErrorActionPreference = "Stop"

function Receive-WebSocketJson {
  param([System.Net.WebSockets.ClientWebSocket]$Socket)

  $stream = New-Object System.IO.MemoryStream
  try {
    do {
      $buffer = New-Object byte[] 65536
      $segment = [System.ArraySegment[byte]]::new($buffer)
      $result = $Socket.ReceiveAsync($segment, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()
      if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
        throw "websocket closed by browser"
      }
      $stream.Write($buffer, 0, $result.Count)
    } while (-not $result.EndOfMessage)

    $text = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
    return $text | ConvertFrom-Json
  } finally {
    $stream.Dispose()
  }
}

function Send-CdpCommand {
  param(
    [System.Net.WebSockets.ClientWebSocket]$Socket,
    [string]$Method,
    [hashtable]$Params = @{}
  )

  $script:NextCdpId += 1
  $id = $script:NextCdpId
  $message = @{
    id = $id
    method = $Method
    params = $Params
  } | ConvertTo-Json -Depth 8 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($message)
  $segment = [System.ArraySegment[byte]]::new($bytes)
  $Socket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null

  while ($true) {
    $response = Receive-WebSocketJson -Socket $Socket
    if ($response.id -eq $id) {
      if ($response.error) {
        throw "CDP $Method failed: $($response.error.message)"
      }
      return $response.result
    }
  }
}

if (-not (Test-Path $Browser)) {
  throw "browser not found: $Browser"
}

$userData = Join-Path $env:TEMP ("gslab-browser-" + [guid]::NewGuid().ToString("N"))
$browserArgs = @(
  "--headless=new",
  "--enable-gpu-rasterization",
  "--ignore-gpu-blocklist",
  "--hide-scrollbars",
  "--remote-debugging-port=$Port",
  "--remote-debugging-address=127.0.0.1",
  "--user-data-dir=$userData",
  "--window-size=$Width,$Height",
  $Url
)

$proc = Start-Process -FilePath $Browser -ArgumentList $browserArgs -PassThru -WindowStyle Hidden
$socket = $null
$script:NextCdpId = 0

try {
  $deadline = (Get-Date).AddSeconds(20)
  $tabs = $null
  do {
    try {
      $tabs = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:$Port/json"
      break
    } catch {
      Start-Sleep -Milliseconds 200
    }
  } while ((Get-Date) -lt $deadline)

  if (-not $tabs) {
    throw "DevTools endpoint did not become ready on port $Port"
  }

  $page = @($tabs | Where-Object { $_.type -eq "page" })[0]
  if (-not $page) {
    $page = @($tabs)[0]
  }
  $socket = [System.Net.WebSockets.ClientWebSocket]::new()
  [void]$socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()

  Send-CdpCommand -Socket $socket -Method "Page.enable" | Out-Null
  Send-CdpCommand -Socket $socket -Method "Runtime.enable" | Out-Null

  $expression = @'
(() => {
  const pill = document.querySelector('#viewerStatusPill')?.textContent || '';
  const overlay = document.querySelector('#sparkOverlay')?.textContent || '';
  const mode = document.querySelector('#viewerModeSparkButton')?.classList.contains('active') ? 'spark' : 'debug';
  return `${mode}|${pill}|${overlay}`;
})()
'@

  $deadline = (Get-Date).AddSeconds($WaitTimeoutSeconds)
  $lastText = ""
  do {
    $result = Send-CdpCommand -Socket $socket -Method "Runtime.evaluate" -Params @{
      expression = $expression
      returnByValue = $true
    }
    $lastText = [string]$result.result.value
    if ($lastText.Contains($WaitText) -or $lastText.Contains("Spark unavailable")) {
      break
    }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)

  if (-not ($lastText.Contains($WaitText) -or $lastText.Contains("Spark unavailable"))) {
    throw "timed out waiting for '$WaitText'; last UI text: '$lastText'"
  }

  if ($ExtraWaitSeconds -gt 0) {
    Start-Sleep -Seconds $ExtraWaitSeconds
  }

  if ($ClickSelector) {
    $clickExpression = @"
(() => {
  const element = document.querySelector('$ClickSelector');
  if (!element) {
    throw new Error('click selector not found: $ClickSelector');
  }
  element.click();
  return true;
})()
"@
    Send-CdpCommand -Socket $socket -Method "Runtime.evaluate" -Params @{
      expression = $clickExpression
      returnByValue = $true
    } | Out-Null
    if ($AfterClickWaitSeconds -gt 0) {
      Start-Sleep -Seconds $AfterClickWaitSeconds
    }
  }

  $screenshot = Send-CdpCommand -Socket $socket -Method "Page.captureScreenshot" -Params @{
    format = "png"
    captureBeyondViewport = $false
  }
  $parent = Split-Path -Parent $Output
  if ($parent) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  [System.IO.File]::WriteAllBytes($Output, [Convert]::FromBase64String($screenshot.data))
  Write-Output "screenshot=$Output"
  Write-Output "ui_text=$lastText"
} finally {
  if ($socket) {
    $socket.Dispose()
  }
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force
  }
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $userData
}
