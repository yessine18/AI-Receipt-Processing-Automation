# Discord Receipt Bot

A Discord bot that integrates with the WhatsApp Invoice backend to process receipts automatically. Upload receipt images directly in Discord and get AI-powered data extraction results instantly.

## Features

- 📸 **Automatic Receipt Processing**: Send receipt images to the bot and get instant AI extraction
- 🔐 **Secure Authentication**: Login with your web app credentials
- 📊 **Receipt Management**: View, search, and delete receipts from Discord
- 🔢 **Short Number System**: Easy reference with #1, #2, #3 instead of long UUIDs
- 📈 **Expense Reports**: Automated weekly summaries and on-demand reports
- 🔄 **Shared Database**: All data syncs with the web interface in real-time

## Prerequisites

- Python 3.9 or higher
- PostgreSQL database (same as main app)
- Discord Bot Token (from Discord Developer Portal)
- Running WhatsApp Invoice backend API

## Discord Bot Setup

### 1. Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name (e.g., "Receipt Bot") and click **Create**
4. Go to the **Bot** section in the left sidebar
5. Click **"Add Bot"** and confirm
6. Under **Token**, click **"Reset Token"** and copy it (you'll need this for `.env`)

### 2. Configure Bot Permissions

In the **Bot** section:
- Enable **"Message Content Intent"** (required for image processing)
- Enable **"Server Members Intent"** (optional, for user tracking)

In the **OAuth2 > URL Generator** section:
- Select scopes: `bot`, `applications.commands`
- Select bot permissions:
  - Read Messages/View Channels
  - Send Messages
  - Attach Files
  - Embed Links
  - Read Message History
- Copy the generated URL at the bottom

### 3. Invite Bot to Your Server

1. Open the URL from step 2 in your browser
2. Select your Discord server
3. Click **Authorize**

## Installation

### 1. Clone and Navigate

```powershell
cd c:\Users\USER\Desktop\WhatsApp_Invoice\discord_bot
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and edit it:

```powershell
cp .env.example .env
```

Edit `.env` with your values:

```ini
# Discord Bot Token from Developer Portal
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Backend API URL (where FastAPI is running)
API_BASE_URL=http://localhost:8000

# PostgreSQL Database URL (same as backend)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/receipts_db

# Schedule Configuration
REPORT_HOUR=9
REPORT_MINUTE=0
REPORT_DAY_OF_WEEK=0
```

**Important Notes:**
- `DISCORD_BOT_TOKEN`: Get this from Discord Developer Portal (step 1 above)
- `API_BASE_URL`: Must match your FastAPI backend URL
- `DATABASE_URL`: Must be identical to backend database URL
- `REPORT_DAY_OF_WEEK`: 0=Monday, 6=Sunday

## Running the Bot

### Start the Bot

```powershell
python bot.py
```

You should see:
```
Logged in as YourBotName#1234 (ID: 123456789)
Bot is ready!
```

### Verify Commands

In Discord, type `/` to see all available commands.

## Usage

### 1. Login to Your Account

```
/login email:your@email.com password:yourpassword
```

You'll receive confirmation that you're logged in.

### 2. Upload Receipt (Two Ways)

**Method A: Auto-Processing (Recommended)**
- Send a receipt image directly to the bot in DMs or channels
- Bot automatically processes it and returns results

**Method B: Manual Command**
```
/receipt [attach image]
```

### 3. View Your Receipts with Short Numbers

```
/receipts
```

Shows your receipts as:
```
#1 - FAKHFAKH YESSINE - €45.00
#2 - Supermarket ABC - €78.50
#3 - Restaurant XYZ - €32.00
```

**Important**: Run `/receipts` first to load the numbered list!

### 4. Use Short Numbers for Easy Access

```
/receipt 1          ← View details of receipt #1
/delete 2           ← Delete receipt #2
```

You can also use full UUIDs if needed.

### 5. Search Receipts

```
/search vendor:Walmart
/search category:Groceries
/search vendor:Walmart category:Groceries
```

### 6. Get Expense Summary

```
/summary period:week
/summary period:month
/summary period:year
```

### 7. Logout

```
/logout
```

### 8. Help

```
/help
```

## Automated Weekly Reports

The bot automatically sends weekly expense summaries every Monday at 9 AM (configurable in `.env`).

## Available Commands (8 Total)

- `/login` - Authenticate with your web app credentials
- `/logout` - Logout from your account
- `/receipts` - List recent receipts with short numbers (#1, #2, #3)
- `/receipt <number>` - View receipt details by number or UUID
- `/search` - Search receipts by vendor and/or category
- `/summary` - Get expense reports (week/month/year)
- `/delete <number>` - Delete a receipt by number or UUID
- `/help` - Show all available commands

**Note**: Run `/receipts` first to load numbered list, then use numbers in other commands!

## Architecture

### Database Sharing

The bot shares the same PostgreSQL database as the web application:

```
PostgreSQL Database (receipts_db)
├── Web App (FastAPI + React) ← reads/writes
└── Discord Bot ← reads/writes
```

All receipts uploaded via Discord appear in the web interface instantly, and vice versa.

### API Communication

The bot communicates with the FastAPI backend via:
- `api_client.py`: HTTP requests for login, upload, search
- `database.py`: Direct database queries for advanced features

### Session Management

- Discord User ID → JWT Token mapping
- Tokens stored in memory (reset on bot restart)
- Users must re-login after bot restarts

### Short Number System

- Run `/receipts` to cache receipts with numbers (#1, #2, #3)
- Use numbers in `/receipt` and `/delete` commands
- Cache is per-user and session-based
- Numbers reset when `/receipts` is run again

## File Structure

```
discord_bot/
├── bot.py              # Main bot file with commands
├── api_client.py       # HTTP client for backend API
├── database.py         # Direct database queries
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .env               # Your configuration (git-ignored)
└── README.md          # This file
```

## Troubleshooting

### Bot doesn't respond to commands

1. Verify bot has **Message Content Intent** enabled in Developer Portal
2. Check bot has proper permissions in the channel
3. Ensure bot is online (check Discord server member list)
4. Wait up to 1 hour for slash commands to sync

### "Receipt number not found in cache" error

You tried to use a short number before loading the cache:

**Solution**: Run `/receipts` first, then use numbers:
```
/receipts           ← Load numbered list
/receipt 1          ← Now this works!
```

### "Not logged in" error

```
/login email:your@email.com password:yourpassword
```

Sessions reset when bot restarts - you need to re-login.

### Image processing fails

1. Verify backend API is running at `http://localhost:8000`
2. Check `API_BASE_URL` in `.env` is correct
3. Ensure Gemini API key is configured in backend
4. Supported formats: JPG, PNG, PDF
5. Check backend logs for detailed errors

### Database connection error

1. Verify PostgreSQL is running: `psql -U postgres`
2. Check `DATABASE_URL` matches backend configuration exactly
3. Ensure database `receipts_db` exists
4. Verify database tables are migrated: `alembic upgrade head`

### Commands not showing up in Discord

1. Restart Discord client
2. Wait up to 1 hour for command sync
3. Check bot logs: should show "Synced 8 command(s)"
4. Try kicking and re-inviting the bot

## Development

### Run in Development Mode

```powershell
# Enable debug logging
$env:LOG_LEVEL="DEBUG"
python bot.py
```

### Test Components

```powershell
# Test API client
python -c "import asyncio; from api_client import APIClient; print('API client imported successfully')"

# Test database connection
python -c "import asyncio; from database import Database; print('Database module imported successfully')"
```

### Bot Features

- **Auto-sync commands**: Bot syncs slash commands on startup
- **Background tasks**: Weekly report scheduler (configurable)
- **Error handling**: Graceful error messages to users
- **Session persistence**: In-memory session storage
- **Cache system**: Receipt number caching per user

## Security Notes

- ⚠️ Never commit `.env` file to version control
- 🔐 Bot stores JWT tokens in memory only
- 🚫 Users must re-authenticate after bot restarts
- 🔒 All API requests use HTTPS in production

## Support

For issues related to:
- **Discord Bot**: Check bot logs and this README
- **Receipt Processing**: Check backend API logs
- **Web Interface**: See main project README

## License

Same license as the main WhatsApp Invoice project.
