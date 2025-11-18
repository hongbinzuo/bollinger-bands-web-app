@echo off
chcp 437 >nul
echo ========================================
echo GitHub Actions Auto Backup Setup Wizard
echo ========================================
echo.

echo Step 1: Get Railway Token
echo Please visit: https://railway.app/account/tokens
echo Create a new token and copy to clipboard
echo.
pause

echo.
echo Step 2: Get Railway Project ID
echo Run in local terminal: railway status
echo Copy the Project ID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
echo.
pause

echo.
echo Step 3: Set GitHub Repository Secrets
echo 1. Go to your GitHub repository
echo 2. Click "Settings" tab
echo 3. Click "Secrets and variables" ^> "Actions" on the left
echo 4. Click "New repository secret"
echo.
echo Add the following two secrets:
echo.
echo Secret 1: RAILWAY_TOKEN
echo - Name: RAILWAY_TOKEN
echo - Value: [Paste your Railway token]
echo.
echo Secret 2: RAILWAY_PROJECT_ID
echo - Name: RAILWAY_PROJECT_ID
echo - Value: [Paste your Project ID]
echo.
pause

echo.
echo Step 4: Push Code to GitHub
echo Now you need to push the code to GitHub to activate Actions
echo.
echo Run the following commands:
echo git add .
echo git commit -m "Add GitHub Actions auto backup feature"
echo git push origin main
echo.
pause

echo.
echo Step 5: Test Backup Function
echo 1. Go to "Actions" tab in your GitHub repository
echo 2. Select "Railway Backup" workflow
echo 3. Click "Run workflow" button
echo 4. Select branch (usually main)
echo 5. Click "Run workflow"
echo.
echo After backup completes, files will be automatically uploaded to:
echo - GitHub Releases (permanent storage)
echo - GitHub Actions Artifacts (retained for 30 days)
echo.
pause

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Now your Railway app data will:
echo - Auto backup daily at 2:00 AM
echo - Allow manual backup triggers
echo - Auto upload backup files to GitHub
echo.
echo If you have issues, please check GITHUB_ACTIONS_SETUP.md file
echo.
pause
