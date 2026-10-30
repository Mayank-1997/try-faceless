param(
    [string]$ApiBase = "http://localhost:8000/api/v1",
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$email = "e2e_$ts@example.com"
$username = "e2e_$ts"
$password = "TestPass123!"

function Api($method, $path, $token, $body) {
    $headers = @{ "Content-Type" = "application/json" }
    if ($token) { $headers["Authorization"] = "Bearer $token" }
    $json = if ($body) { $body | ConvertTo-Json -Depth 8 } else { $null }
    return Invoke-RestMethod -Method $method -Uri "$ApiBase$path" -Headers $headers -Body $json
}

Write-Host "== Register =="
Api POST "/auth/register" $null @{ email = $email; username = $username; password = $password; first_name = "E2E"; last_name = "Tester" } | Out-Null

Write-Host "== Login =="
$login = Api POST "/auth/login" $null @{ email = $email; password = $password }
$token = $login.access_token
Write-Host "  token acquired"

Write-Host "== Create project =="
$proj = Api POST "/projects" $token @{ title = "E2E Real Workflow $ts"; description = "AI in healthcare"; content_type = "youtube_video"; video_style = "mixed" }
$projectId = $proj.id
Write-Host "  project_id=$projectId"

Write-Host "== Start workflow =="
$start = Api POST "/projects/$projectId/workflow/start" $token
Write-Host "  status=$($start.status) step=$($start.current_step)"

Write-Host "== Poll workflow =="
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$last = ""
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    $wf = Api GET "/projects/$projectId/workflow" $token
    $line = "status=$($wf.status) step=$($wf.current_step)"
    if ($line -ne $last) { Write-Host "  $line"; $last = $line }
    if ($wf.status -eq "completed") {
        Write-Host "RESULT: COMPLETED project_id=$projectId"
        exit 0
    }
    if ($wf.status -eq "failed") {
        Write-Host "RESULT: FAILED reason=$($wf.failure_reason) project_id=$projectId"
        exit 1
    }
}
Write-Host "RESULT: TIMEOUT project_id=$projectId"
exit 2
