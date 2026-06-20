#Requires -RunAsAdministrator
param(
  [int]$Port = 8769,
  [string]$ListenAddress = "0.0.0.0",
  [string]$ConnectAddress = "",
  [string]$FirewallRuleName = "Gaussian Splat Lab UI",
  [switch]$Remove
)

$ErrorActionPreference = "Stop"

function Get-WslAddress {
  $raw = & wsl.exe hostname -I
  $addresses = @($raw -split "\s+" | Where-Object {
    $_ -match "^\d{1,3}(\.\d{1,3}){3}$" -and
    $_ -ne "127.0.0.1" -and
    $_ -ne "10.255.255.254"
  })
  if (-not $addresses -or $addresses.Count -eq 0) {
    throw "Could not detect the WSL IP address. Pass -ConnectAddress explicitly."
  }
  return $addresses[0]
}

function Get-LanAddresses {
  Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
      $_.IPAddress -notlike "127.*" -and
      $_.IPAddress -notlike "169.254*" -and
      $_.InterfaceAlias -notlike "vEthernet*" -and
      $_.InterfaceAlias -notmatch "VirtualBox|VMware|Hyper-V"
    } |
    Select-Object -ExpandProperty IPAddress
}

if (-not $ConnectAddress) {
  $ConnectAddress = Get-WslAddress
}

$netsh = Join-Path $env:SystemRoot "System32\netsh.exe"

if ($Remove) {
  & $netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$Port | Out-Null
  Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  Write-Host "Removed LAN exposure for port $Port."
  return
}

& $netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$Port | Out-Null
& $netsh interface portproxy add v4tov4 listenaddress=$ListenAddress listenport=$Port connectaddress=$ConnectAddress connectport=$Port | Out-Null

$existingRule = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
if ($existingRule) {
  Set-NetFirewallRule -DisplayName $FirewallRuleName -Enabled True -Action Allow
} else {
  New-NetFirewallRule `
    -DisplayName $FirewallRuleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Port `
    -Profile Private | Out-Null
}

Write-Host "Gaussian Splat Lab UI is forwarded to WSL $ConnectAddress on port $Port."
foreach ($address in Get-LanAddresses) {
  Write-Host "Try from another device: http://$address`:$Port/"
}
