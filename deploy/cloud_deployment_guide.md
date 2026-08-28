# 24/7 Cloud Deployment Guide (Delta Exchange Bot)

To keep your bot running **24/7 continuously even when your computer is turned off, asleep, or disconnected**, you must host it on a **Cloud Server (VPS)** or a **Cloud Platform**.

---

## 3 Best Ways to Run 24/7 (Choose One)

| Option | Cost | Difficulty | Best For |
|---|---|---|---|
| **Option 1: Cheap Linux VPS (Hetzner / DigitalOcean / Hostinger)** | ~$3 - $4 / month | Very Easy | **Recommended** (Maximum reliability, 99.99% uptime) |
| **Option 2: Free Tier VPS (AWS / Oracle Cloud / Google Cloud)** | **FREE** ($0) | Easy | 100% Free 24/7 running |
| **Option 3: 1-Click Cloud Platform (Render / Railway)** | Free / $5 / mo | Easiest (No Linux needed) | Connect to GitHub & deploy |

---

## Option 1 & 2: Deploy on any Linux VPS (5-Minute Setup)

### Step 1: Get a VPS Server
1. Create an account on any cloud provider:
   - **Free Options**: [AWS Free Tier](https://aws.amazon.com/free/) (EC2 `t2.micro`), [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/), or [Google Cloud Free Tier](https://cloud.google.com/free).
   - **Cheap / Fast Options ($3 - $5/mo)**: [Hetzner Cloud](https://www.hetzner.com/cloud) (CX22), [DigitalOcean Droplet](https://www.digitalocean.com/) ($4/mo), or [Hostinger](https://www.hostinger.com/).
2. Select OS: **Ubuntu 22.04 LTS** or **Ubuntu 24.04 LTS**.

### Step 2: Connect to your Server
Open Terminal or PowerShell on your computer and connect via SSH:
```bash
ssh root@YOUR_SERVER_IP
```

### Step 3: Copy Your Bot Files to the Server
From your local computer terminal, copy the project folder to the server:
```bash
scp -r "d:/DT SCRIPT" root@YOUR_SERVER_IP:/root/delta-bot
```
*(Or clone it directly from your GitHub repository if you pushed it)*

### Step 4: Run the 1-Click Setup Script
On the server, run:
```bash
cd /root/delta-bot
chmod +x deploy/setup_vps.sh
./deploy/setup_vps.sh
```

### Step 5: Enter your Delta API Keys in `.env`
```bash
nano .env
```
Fill in your API keys:
```ini
DELTA_ENVIRONMENT=india          # or 'global'
DELTA_API_KEY=your_key_here
DELTA_API_SECRET=your_secret_here
TRADING_SYMBOL=BTCUSD
ORDER_SIZE=1
LEVERAGE=10
```
Press `Ctrl+O`, then `Enter` to save, and `Ctrl+X` to exit.

### Step 6: Restart the 24/7 Service
```bash
sudo systemctl restart delta-bot
```

**That is all!** You can now close your terminal and turn off your computer. The bot is running 24/7 in the cloud.

---

## Useful Commands on VPS:

| Task | Command |
|---|---|
| **View Live Real-Time Logs** | `sudo journalctl -u delta-bot -f` |
| **Check Bot Status** | `sudo systemctl status delta-bot` |
| **Restart Bot** | `sudo systemctl restart delta-bot` |
| **Stop Bot** | `sudo systemctl stop delta-bot` |

---

## Alternative: Run with Docker Compose (1 Command)

If your server has Docker installed:
```bash
# 1. Edit .env
nano .env

# 2. Launch in background
docker compose up -d

# 3. View live logs
docker compose logs -f
```

---

## Option 3: Deploy on Render.com (No Terminal / 1-Click)

1. Push your `DT SCRIPT` folder to a private GitHub repository.
2. Go to [Render.com](https://render.com/) and click **New +** $ightarrow$ **Background Worker** (for Standalone Bot) or **Web Service** (for Webhook Mode).
3. Connect your GitHub repository.
4. Set:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m bot.standalone_bot`
5. In the **Environment Variables** section, add:
   - `DELTA_ENVIRONMENT`: `india` (or `global`)
   - `DELTA_API_KEY`: `your_key`
   - `DELTA_API_SECRET`: `your_secret`
   - `TRADING_SYMBOL`: `BTCUSD`
   - `ORDER_SIZE`: `1`
   - `LEVERAGE`: `10`
6. Click **Deploy**. Render will run the bot 24/7 in the cloud continuously.
