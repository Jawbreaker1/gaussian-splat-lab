param(
  [Parameter(Mandatory = $true)][string]$Url,
  [string]$Browser = "C:\Program Files\Google\Chrome\Application\chrome.exe",
  [int]$Port = 9234,
  [int]$Width = 1440,
  [int]$Height = 1000,
  [string]$WaitText = "ultra inspect",
  [int]$WaitTimeoutSeconds = 180
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
  } | ConvertTo-Json -Depth 32 -Compress
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

$userData = Join-Path $env:TEMP ("gslab-controls-" + [guid]::NewGuid().ToString("N"))
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

  $waitExpression = @'
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
      expression = $waitExpression
      returnByValue = $true
    }
    $lastText = [string]$result.result.value
    if ($lastText.Contains($WaitText) -or $lastText.Contains("Spark unavailable")) {
      break
    }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)

  if (-not ($lastText.Contains($WaitText))) {
    throw "timed out waiting for '$WaitText'; last UI text: '$lastText'"
  }

  $testExpression = @'
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const debug = window.__gslabViewerDebug;
  if (!debug?.getSparkNavigationState) throw new Error('viewer debug state is unavailable');

  const byId = (id) => {
    const element = document.querySelector(id);
    if (!element) throw new Error(`missing control ${id}`);
    return element;
  };
  const state = () => {
    const value = debug.getSparkNavigationState();
    if (!value) throw new Error('navigation state is unavailable');
    return value;
  };
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  const finiteState = (value) => (
    Number.isFinite(value.targetDistance)
      && Number.isFinite(value.rollDegrees)
      && value.position.every(Number.isFinite)
      && value.target.every(Number.isFinite)
      && value.up.every(Number.isFinite)
      && value.navigationUp.every(Number.isFinite)
  );
  const run = async (label, selector, limits) => {
    const before = state();
    byId(selector).click();
    await sleep(220);
    const after = state();
    if (!finiteState(after)) throw new Error(`${label}: non-finite camera state`);
    const positionDelta = distance(before.position, after.position);
    const targetDelta = distance(before.target, after.target);
    const distanceDelta = Math.abs(before.targetDistance - after.targetDistance);
    const result = {
      label,
      mode: after.mode,
      positionDelta: Number(positionDelta.toFixed(6)),
      targetDelta: Number(targetDelta.toFixed(6)),
      distanceDelta: Number(distanceDelta.toFixed(6)),
      targetDistance: after.targetDistance,
    };
    if (positionDelta > limits.position) throw new Error(`${label}: position jump ${positionDelta.toFixed(4)} > ${limits.position}`);
    if (targetDelta > limits.target) throw new Error(`${label}: target jump ${targetDelta.toFixed(4)} > ${limits.target}`);
    if (distanceDelta > limits.distance) throw new Error(`${label}: distance jump ${distanceDelta.toFixed(4)} > ${limits.distance}`);
    if (after.targetDistance > limits.maxTargetDistance) throw new Error(`${label}: target distance ${after.targetDistance} > ${limits.maxTargetDistance}`);
    return result;
  };
  const setSensitivity = async (percent) => {
    const input = byId('#viewerSensitivityInput');
    const output = byId('#viewerSensitivityValue');
    input.value = String(percent);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await sleep(120);
    const navState = state();
    const expected = percent / 100;
    if (Math.abs(navState.navigationSensitivity - expected) > 0.001) {
      throw new Error(`navigation sensitivity did not apply: ${navState.navigationSensitivity} != ${expected}`);
    }
    if (output.textContent.trim() !== `${percent}%`) {
      throw new Error(`navigation sensitivity label did not update: ${output.textContent}`);
    }
  };

  const results = [];
  await setSensitivity(35);
  await setSensitivity(55);
  byId('#viewerModeSparkButton').click();
  byId('#viewerNavWalkButton').click();
  await sleep(500);
  byId('#viewerResetButton').click();
  await sleep(500);
  if (typeof debug.lookPixels !== 'function') throw new Error('viewer debug lookPixels hook is unavailable');
  const resetRoll = Math.abs(state().rollDegrees);
  if (resetRoll > 1.5) throw new Error(`walk reset left camera rolled by ${resetRoll.toFixed(3)} degrees`);
  for (let index = 0; index < 30; index += 1) {
    debug.lookPixels(24, 0);
    await sleep(12);
  }
  const horizontalSwipeRight = state();
  if (Math.abs(horizontalSwipeRight.rollDegrees) > 1.5) {
    throw new Error(`horizontal walk swipe accumulated roll: ${horizontalSwipeRight.rollDegrees.toFixed(3)} degrees`);
  }
  for (let index = 0; index < 30; index += 1) {
    debug.lookPixels(-24, 0);
    await sleep(12);
  }
  const horizontalSwipeReturn = state();
  if (Math.abs(horizontalSwipeReturn.rollDegrees) > 1.5) {
    throw new Error(`horizontal walk swipe return left roll: ${horizontalSwipeReturn.rollDegrees.toFixed(3)} degrees`);
  }

  const walkMoveLimits = { position: 0.16, target: 0.2, distance: 0.04, maxTargetDistance: 8.05 };
  const walkLookLimits = { position: 0.025, target: 0.16, distance: 0.04, maxTargetDistance: 8.05 };
  for (const [label, selector, limits] of [
    ['walk pan left', '#viewerPanLeftButton', walkMoveLimits],
    ['walk pan right', '#viewerPanRightButton', walkMoveLimits],
    ['walk pan up', '#viewerPanUpButton', walkMoveLimits],
    ['walk pan down', '#viewerPanDownButton', walkMoveLimits],
    ['walk look left', '#viewerOrbitLeftButton', walkLookLimits],
    ['walk look right', '#viewerOrbitRightButton', walkLookLimits],
    ['walk look up', '#viewerOrbitUpButton', walkLookLimits],
    ['walk look down', '#viewerOrbitDownButton', walkLookLimits],
    ['walk zoom in', '#viewerZoomInButton', walkMoveLimits],
    ['walk zoom out', '#viewerZoomOutButton', walkMoveLimits],
  ]) {
    results.push(await run(label, selector, limits));
  }

  byId('#viewerPanLeftButton').click();
  await sleep(180);
  const beforeKeyboard = state();
  document.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', key: 'w', bubbles: true }));
  await sleep(420);
  document.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyW', key: 'w', bubbles: true }));
  await sleep(120);
  const afterKeyboard = state();
  const keyboardPositionDelta = distance(beforeKeyboard.position, afterKeyboard.position);
  if (keyboardPositionDelta < 0.03) throw new Error(`walk keyboard did not move after button focus: ${keyboardPositionDelta.toFixed(4)}`);
  if (keyboardPositionDelta > 0.35) throw new Error(`walk keyboard moved too far after button focus: ${keyboardPositionDelta.toFixed(4)}`);

  byId('#viewerResetButton').click();
  await sleep(500);
  byId('#viewerNavOrbitButton').click();
  await sleep(500);

  const orbitMoveLimits = { position: 0.18, target: 0.18, distance: 0.05, maxTargetDistance: 8.05 };
  const orbitRotateLimits = { position: 0.35, target: 0.025, distance: 0.05, maxTargetDistance: 8.05 };
  const orbitZoomLimits = { position: 0.45, target: 0.025, distance: 0.45, maxTargetDistance: 8.05 };
  for (const [label, selector, limits] of [
    ['orbit pan left', '#viewerPanLeftButton', orbitMoveLimits],
    ['orbit pan right', '#viewerPanRightButton', orbitMoveLimits],
    ['orbit pan up', '#viewerPanUpButton', orbitMoveLimits],
    ['orbit pan down', '#viewerPanDownButton', orbitMoveLimits],
    ['orbit rotate left', '#viewerOrbitLeftButton', orbitRotateLimits],
    ['orbit rotate right', '#viewerOrbitRightButton', orbitRotateLimits],
    ['orbit rotate up', '#viewerOrbitUpButton', orbitRotateLimits],
    ['orbit rotate down', '#viewerOrbitDownButton', orbitRotateLimits],
    ['orbit zoom in', '#viewerZoomInButton', orbitZoomLimits],
    ['orbit zoom out', '#viewerZoomOutButton', orbitZoomLimits],
  ]) {
    results.push(await run(label, selector, limits));
  }

  byId('#viewerModeDebugButton').click();
  let debugState = null;
  for (let attempt = 0; attempt < 180; attempt += 1) {
    await sleep(500);
    debugState = debug.getUiState();
    if (debugState.mode === 'debug' && debugState.debugPointCount > 0) break;
  }
  if (!debugState || debugState.mode !== 'debug') throw new Error('debug mode did not activate');
  if (!(debugState.debugPointCount > 0)) throw new Error('debug point cloud did not load any points');

  byId('#viewerModeSparkButton').click();
  await sleep(500);

  return { status: 'pass', count: results.length, results, keyboardPositionDelta, debugState, finalState: state() };
})()
'@

  $test = Send-CdpCommand -Socket $socket -Method "Runtime.evaluate" -Params @{
    expression = $testExpression
    awaitPromise = $true
    returnByValue = $true
  }
  if ($test.exceptionDetails) {
    throw "viewer control validation failed: $($test.exceptionDetails.text)"
  }
  $value = $test.result.value
  if (-not $value -or $value.status -ne "pass") {
    throw "viewer control validation did not return pass"
  }

  Write-Output ("viewer_control_validation=passed")
  Write-Output ("tested_controls={0}" -f $value.count)
  Write-Output ("max_position_delta={0}" -f (($value.results | Measure-Object -Property positionDelta -Maximum).Maximum))
  Write-Output ("max_target_delta={0}" -f (($value.results | Measure-Object -Property targetDelta -Maximum).Maximum))
  Write-Output ("max_distance_delta={0}" -f (($value.results | Measure-Object -Property distanceDelta -Maximum).Maximum))
  Write-Output ("keyboard_position_delta={0}" -f $value.keyboardPositionDelta)
  Write-Output ("debug_point_count={0}" -f $value.debugState.debugPointCount)
  Write-Output ("final_mode={0}" -f $value.finalState.mode)
  Write-Output ("final_target_distance={0}" -f $value.finalState.targetDistance)
} finally {
  if ($socket) {
    $socket.Dispose()
  }
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force
  }
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $userData
}
