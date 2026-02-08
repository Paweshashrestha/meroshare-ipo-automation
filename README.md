# MeroShare IPO Automation

Automated IPO application system for MeroShare (Nepal Stock Exchange) that checks for available IPOs and automatically submits applications based on predefined criteria.

## Setup (new user)

1. **Clone and enter the project**
   ```bash
   git clone <repo-url>
   cd ipo
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
   cp config.yaml.example config.yaml
   ```
   Edit `config.yaml`: set MeroShare account(s) and Telegram. See [Configuration](#configuration) and [Multiple accounts](#multiple-accounts) below. Use `headless: true` for no browser window, `false` to watch.

5. **Run once (manual test)**
   ```bash
   python3 src/meroshare/check.py
   ```

6. **Optional: daily run at 12:45 (Linux with systemd)**
   From project root:
   ```bash
   sudo ./setup_timer.sh
   sudo timedatectl set-timezone Asia/Kathmandu   # for Nepal time
   ```
   Check: `systemctl list-timers ipo-check.timer` — next run time. Logs: `sudo journalctl -u ipo-check.service`.

## Features

- **Automated IPO Detection**: Checks for available IPOs matching specific criteria (Rs. 100 per share, IPO type, Ordinary Shares)
- **Multi-Account Support**: Checks with one account, applies with all configured accounts if IPO is found
- **Form Auto-Fill**: Automatically fills application forms with account details
- **Telegram Notifications**: Real-time notifications via Telegram bot
- **Error Handling**: Robust error handling with detailed logging
- **Scheduled Execution**: Can run as a systemd service for automated daily checks

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

### Automated (daily at 12:45)

```bash
./setup_timer.sh
```

Uses a systemd timer to run the IPO check once daily at 12:45 (set timezone to Asia/Kathmandu for Nepal time).

## Project Structure

```
ipo/
├── src/
│   ├── meroshare/
│   │   ├── browser.py      # Browser automation
│   │   ├── login.py        # MeroShare login
│   │   └── check.py        # Main IPO checking logic
│   ├── scheduler/
│   │   └── run_once.py     # One-shot run (used by systemd timer)
│   └── config.py           # Configuration management
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── setup_timer.sh          # Systemd timer setup (daily 12:45)
└── systemd/                # ipo-check.service, ipo-check.timer
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
- **Systemd**: Service management

## License

Private project

