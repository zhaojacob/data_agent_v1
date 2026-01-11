# ============================================================
# Docker Cleanup Script (PowerShell)
# ============================================================
# Run this script periodically to free up disk space
# Usage: Right-click -> Run with PowerShell
#    or: powershell -ExecutionPolicy Bypass -File docker_cleanup.ps1
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           Docker Cleanup Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Show current disk usage
Write-Host "[1/4] Current Docker disk usage:" -ForegroundColor Yellow
docker system df
Write-Host ""

# Step 2: Remove stopped containers
Write-Host "[2/4] Removing stopped containers..." -ForegroundColor Yellow
docker container prune -f
Write-Host ""

# Step 3: Remove unused images
Write-Host "[3/4] Removing dangling images..." -ForegroundColor Yellow
docker image prune -f
Write-Host ""

# Step 4: Remove build cache
Write-Host "[4/4] Removing build cache..." -ForegroundColor Yellow
docker builder prune -f
Write-Host ""

# Show final disk usage
Write-Host "============================================================" -ForegroundColor Green
Write-Host "           Cleanup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Final Docker disk usage:" -ForegroundColor Yellow
docker system df
Write-Host ""

# Optional: Deep clean (uncomment if needed)
# Write-Host "For deep clean (removes ALL unused images), run:" -ForegroundColor Magenta
# Write-Host "  docker system prune -a" -ForegroundColor White

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
