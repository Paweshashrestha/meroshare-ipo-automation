# MeroShare IPO Automation

Automated IPO application system for MeroShare (Nepal Stock Exchange) that checks for available IPOs and automatically submits applications based on predefined criteria.

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

2. Edit `config.yaml` with your account details:

```yaml
meroshare:
  accounts:
    - username: "your_username"
      password: "your_password"
      dp_name: "BANK NAME"
      bank_name: "BANK NAME"
      crn: "CRN_NUMBER"
      boid: "BOID_NUMBER"
      transaction_pin: "PIN"
      applied_kitta: "10"

telegram:
  bot_token: "your_bot_token"
  chat_id: "your_chat_id"
```

## Usage

### Manual Run

```bash
python3 src/meroshare/check.py
```

### Automated Scheduler

```bash
# Setup systemd service
./setup_scheduler.sh

# Or run scheduler directly
python3 src/scheduler/run.py
```

## Project Structure

```
ipo/
├── src/
│   ├── meroshare/
│   │   ├── browser.py      # Browser automation
│   │   ├── login.py        # MeroShare login
│   │   └── check.py        # Main IPO checking logic
│   ├── scheduler/
│   │   └── run.py          # Scheduled execution
│   └── config.py           # Configuration management
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
└── setup_scheduler.sh      # Service setup script
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

