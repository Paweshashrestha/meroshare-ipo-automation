# MeroShare IPO Automation

Automated IPO application system for MeroShare (Nepal Stock Exchange) that checks for available IPOs and automatically submits applications based on predefined criteria.
**For personal use only.** Fork the repo on GitHub, then clone your fork to your machine; do not use it for commercial or unauthorized purposes.

## Setup (new user)

1. **Clone and enter the project**
   ```bash
   git clone https://github.com/YOUR_USERNAME/meroshare-ipo-automation.git
   cd meroshare-ipo-automation
   ```

2. **Python 3.8+ and virtualenv (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   # or: venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Config**
   ```bash
   cp config.yaml.example config.yaml   # Linux/macOS
   copy config.yaml.example config.yaml # Windows
   ```
   Edit `config.yaml`: set MeroShare account(s) and Telegram. See [Configuration](#configuration) and [Multiple accounts](#multiple-accounts) below. Use `headless: true` for no browser window, `false` to watch.

5. **Run once (manual test)**
   ```bash
   python3 src/meroshare/check.py
   ```
   Windows: `run_check.bat` or `python src\meroshare\check.py`

6. **Optional: daily run at 11:11 Nepal time**
   - **Linux**: From project root run `sudo ./setup_timer.sh`. Uses systemd; no need to change timezone. Check: `sudo systemctl list-timers ipo-check.timer`. Logs: `sudo journalctl -u ipo-check.service`.
   - **macOS**: From project root run `./setup_timer_macos.sh`. Uses LaunchAgent and runs at 11:11 local time; set timezone to Asia/Kathmandu for 11:11 Nepal time.
   - **Windows**: Run PowerShell as Administrator, then `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` (if needed), and `.\setup_timer_windows.ps1`. Task runs daily at 11:11 AM local time; set system timezone to Nepal (UTC+5:45) for 11:11 Nepal time. View in Task Scheduler → Task Scheduler Library → IPO-Check-MeroShare.

## Features

- **Automated IPO Detection**: Checks for available IPOs matching specific criteria (Rs. 100 per share, IPO type, Ordinary Shares)
- **Multi-Account Support**: Checks with one account, applies with all configured accounts if IPO is found
- **Form Auto-Fill**: Automatically fills application forms with account details
- **Telegram Notifications**: Real-time notifications via Telegram bot
- **Error Handling**: Robust error handling with detailed logging
- **Scheduled Execution**: systemd (Linux), LaunchAgent (macOS), or Task Scheduler (Windows) runs the check daily

## Requirements

- Python 3.8+
- Playwright
- Required packages listed in `requirements.txt`

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

## Configuration

1. Copy the example config file:
   ```bash
   cp config.yaml.example config.yaml
   ```

2. Edit `config.yaml` with your account details and Telegram (see below).

### Multiple accounts

List all MeroShare accounts under `meroshare.accounts`. The **first** account is used to log in and check for IPOs; **all** accounts are used to apply if a matching IPO is found.

```yaml
meroshare:
  accounts:
    - account_name: "My account"
      username: "user1"
      password: "pass1"
      dp_name: "BANK NAME"
      bank_name: "BANK NAME"
      crn: "CRN_NUMBER"
      boid: "BOID_NUMBER"
      transaction_pin: "PIN"
      applied_kitta: "10"
    - account_name: "Brother's account"
      username: "user2"
      password: "pass2"
      dp_name: "BANK NAME"
      bank_name: "BANK NAME"
      crn: "CRN_NUMBER"
      boid: "BOID_NUMBER"
      transaction_pin: "PIN"
      applied_kitta: "10"
    # Add more accounts with the same fields.

telegram:
  bot_token: "your_bot_token"
  chat_id: "your_chat_id"

headless: true
```

- **account_name** (optional): Label shown in Telegram and logs (e.g. "My account", "Brother's account"). If omitted, username is used.
- Each account must have: `username`, `password`, `dp_name`, `bank_name`, `crn`, `boid`, `transaction_pin`, and optionally `applied_kitta` (default 10).

## Usage

### Manual Run

```bash
python3 src/meroshare/check.py
```

Windows: double-click `run_check.bat` or run `python src\meroshare\check.py` from the project folder.

### Automated (daily at 11:11 Nepal time)

- **Linux**: From project root run `sudo ./setup_timer.sh`. Uses systemd timer.
- **macOS**: From project root run `./setup_timer_macos.sh`. Uses LaunchAgent timer.
- **Windows**: Run `.\setup_timer_windows.ps1` in PowerShell as Administrator. Set timezone to Nepal for 11:11 Nepal time.

## Checking if Windows works

- **On a Windows PC**: Open Command Prompt in the project folder, run `run_check.bat`. If it starts Python and runs (even if it later fails on login/config), paths and scripts work. To test the scheduler script: PowerShell as Administrator → `.\setup_timer_windows.ps1` → open Task Scheduler and confirm task "IPO-Check-MeroShare" exists.
- **Without Windows**: Push the repo to GitHub and open the **Actions** tab. Run the **Windows** workflow (it uses `config.yaml.example` only—your real `config.yaml` is gitignored and never uploaded). If the run has a **green check**, the smoke test passed and the Windows setup is valid. If it’s **red**, open the run and check which step failed.

## Project Structure

```
meroshare-ipo-automation/
├── src/
│   ├── meroshare/
│   │   ├── browser.py      # Browser automation
│   │   ├── login.py        # MeroShare login
│   │   └── check.py        # Main IPO checking logic
│   ├── scheduler/
│   │   └── run_once.py     # One-shot run (used by systemd timer)
│   └── config.py           # Configuration management
├── config.yaml             # Configuration file (create from config.yaml.example)
├── requirements.txt       # Python dependencies
├── run_check.bat          # Windows: run check once (double-click or Task Scheduler)
├── setup_timer.sh         # Linux: systemd timer setup (daily 11:11 Nepal time)
├── setup_timer_macos.sh   # macOS: LaunchAgent setup (daily 11:11 local time)
├── setup_timer_windows.ps1 # Windows: Task Scheduler setup (daily 11:11 local time)
└── systemd/               # ipo-check.service, ipo-check.timer (Linux)
```

## How It Works

1. Logs into MeroShare using the first account
2. Navigates to ASBA section
3. Checks for available IPOs
4. Validates IPO criteria (Price: Rs. 100, Type: IPO, Share: Ordinary)
5. If matching IPO found:
   - Applies with first account
   - Logs into each additional account
   - Applies for the same IPO with all accounts
6. Sends Telegram notifications for each application

## Technologies Used

- **Python 3**: Core language
- **Playwright**: Browser automation
- **YAML**: Configuration management
- **Telegram Bot API**: Notifications
- **Systemd** (Linux) / **LaunchAgent** (macOS) / **Task Scheduler** (Windows): Scheduled runs

## License

Private project

