# 백엔드(uvicorn) + 프론트엔드(vite)를 한 번에 띄우는 Windows용 개발 스크립트.
# 보통은 dev.bat 을 더블클릭하면 이 파일이 실행됩니다.
#
#   .\dev.ps1                # 의존성 확인 후 두 서버 모두 실행
#   .\dev.ps1 -NoReload      # 백엔드 자동 재시작 끄기
#   .\dev.ps1 -SkipInstall   # 의존성 설치/동기화 건너뛰기
#   .\dev.ps1 -NoBrowser     # 브라우저 자동 열기 끄기

param(
    [int]$BackendPort = 8100,
    [int]$FrontendPort = 5174,
    [string]$BackendHost = "0.0.0.0",
    [string]$PythonVersion = "3.12",
    [switch]$NoReload,
    [switch]$SkipInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$backend = $null
$frontend = $null

function Write-Info  { param($m) Write-Host "[dev] $m" -ForegroundColor Cyan }
function Write-Warn2 { param($m) Write-Host "[dev] $m" -ForegroundColor Yellow }
function Write-Err   { param($m) Write-Host "[dev] $m" -ForegroundColor Red }

function Stop-Servers {
    foreach ($proc in @($frontend, $backend)) {
        if ($proc -and -not $proc.HasExited) {
            # 자식 프로세스(uv -> uvicorn, npm -> vite)까지 함께 정리합니다.
            try { taskkill /PID $proc.Id /T /F 2>$null | Out-Null } catch { }
        }
    }
}

function Test-PortInUse {
    param([int]$Port)
    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Assert-Command {
    param([string]$Name, [string]$HowToInstall)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Err "'$Name' 을(를) 찾을 수 없습니다."
        Write-Host ""
        Write-Host $HowToInstall
        Write-Host ""
        Write-Host "설치한 뒤 이 창을 닫고 dev.bat 을 다시 실행해 주세요."
        Read-Host "엔터를 누르면 종료합니다"
        exit 1
    }
}

try {
    # --- 사전 점검 -----------------------------------------------------------

    Assert-Command "uv" @"
uv(파이썬 도구)가 필요합니다. PowerShell 을 열고 아래 한 줄을 붙여넣어 실행하세요.

    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

설치 후에는 PowerShell 창을 반드시 새로 열어야 인식됩니다.
"@

    Assert-Command "npm" @"
Node.js 가 필요합니다. 아래 주소에서 LTS 버전을 내려받아 설치하세요.

    https://nodejs.org/

설치 화면은 전부 '다음(Next)' 으로 넘어가면 됩니다.
설치 후에는 컴퓨터를 한 번 재시작하거나 PowerShell 창을 새로 열어 주세요.
"@

    if (-not (Test-Path (Join-Path $root ".env"))) {
        if (Test-Path (Join-Path $root ".env.example")) {
            Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env")
            Write-Warn2 ".env 파일을 새로 만들었습니다."
            Write-Host ""
            Write-Host "  아직 API 키가 비어 있어서 문제 생성이 되지 않습니다." -ForegroundColor Yellow
            Write-Host "  1) 이 폴더의 .env 파일을 메모장으로 엽니다."
            Write-Host "  2) GOOGLE_API_KEY= 뒤에 발급받은 키를 붙여넣고 저장합니다."
            Write-Host "     키 발급: https://aistudio.google.com/apikey"
            Write-Host "  3) 저장한 뒤 dev.bat 을 다시 실행하세요."
            Write-Host ""
            Read-Host "엔터를 누르면 종료합니다"
            exit 1
        }
        Write-Warn2 ".env 파일이 없습니다. 기본값으로 실행합니다."
    }

    foreach ($port in @($BackendPort, $FrontendPort)) {
        if (Test-PortInUse -Port $port) {
            Write-Err "포트 $port 를 이미 다른 프로그램이 쓰고 있습니다."
            Write-Host "  이 프로그램을 이미 켜 두었는지 확인하거나, 컴퓨터를 재시작한 뒤 다시 시도해 주세요."
            Read-Host "엔터를 누르면 종료합니다"
            exit 1
        }
    }

    # --- 의존성 --------------------------------------------------------------

    if (-not $SkipInstall) {
        Write-Info "파이썬 의존성을 준비하고 있습니다... (처음 한 번은 몇 분 걸릴 수 있습니다)"
        & uv sync --frozen --python $PythonVersion
        if ($LASTEXITCODE -ne 0) { throw "uv sync 실패" }

        $nodeModules = Join-Path $root "frontend\node_modules"
        if (-not (Test-Path $nodeModules)) {
            Write-Info "프론트엔드 의존성을 설치하고 있습니다... (처음 한 번은 몇 분 걸릴 수 있습니다)"
            Push-Location (Join-Path $root "frontend")
            & npm ci
            $npmExit = $LASTEXITCODE
            Pop-Location
            if ($npmExit -ne 0) { throw "npm ci 실패" }
        } else {
            Write-Info "프론트엔드 의존성 최신 상태 - 설치 건너뜀."
        }
    }

    # --- 실행 ----------------------------------------------------------------

    $env:BACKEND_PORT = "$BackendPort"   # vite.config.js 가 proxy 대상 포트로 사용
    $env:UV_PROJECT_ENVIRONMENT = ".venv"

    $uvicornArgs = @("run", "--no-sync", "uvicorn", "backend.main:app", "--host", $BackendHost, "--port", "$BackendPort")
    if (-not $NoReload) { $uvicornArgs += "--reload" }

    Write-Info "백엔드를 시작합니다 (포트 $BackendPort)..."
    $backend = Start-Process -FilePath "uv" -ArgumentList $uvicornArgs -PassThru -NoNewWindow

    Write-Info "프론트엔드를 시작합니다 (포트 $FrontendPort)..."
    $frontend = Start-Process -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--port", "$FrontendPort") `
        -WorkingDirectory (Join-Path $root "frontend") -PassThru -NoNewWindow

    # 백엔드가 응답할 때까지 대기 (최대 60초)
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        if ($backend.HasExited) { break }
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    Write-Host ""
    if ($ready) {
        Write-Host "  준비 완료!" -ForegroundColor Green
    } else {
        Write-Warn2 "백엔드 응답을 확인하지 못했습니다. 아래 주소를 직접 열어 보세요."
    }
    Write-Host ""
    Write-Host "  화면 주소   http://localhost:$FrontendPort" -ForegroundColor Green
    Write-Host "  (API)       http://localhost:$BackendPort"
    Write-Host ""
    Write-Host "  종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요."
    Write-Host ""

    if (-not $NoBrowser -and $ready) {
        Start-Process "http://localhost:$FrontendPort"
    }

    # 둘 중 하나라도 죽으면 전체 종료
    while ($true) {
        if ($backend.HasExited -or $frontend.HasExited) {
            Write-Warn2 "서버 중 하나가 종료되어 나머지도 함께 내립니다."
            break
        }
        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Err $_.Exception.Message
    Read-Host "엔터를 누르면 종료합니다"
}
finally {
    Write-Info "정리 중..."
    Stop-Servers
}
