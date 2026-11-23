import os
import logging
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

from news_fetcher import fetch_league_news, fetch_team_news

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Persistent user store ----------
# Simple JSON file store (for Railway volume). For scale, use Redis/DB.
DATA_FILE = Path("users.json")

def load_users():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_users(users):
    DATA_FILE.write_text(json.dumps(users, indent=2))

USERS = load_users()

def save_user(uid, data):
    USERS[str(uid)] = data
    save_users(USERS)

# ---------- Static data ----------
LEAGUES = {
    "Premier League": "premier-league",
    "La Liga": "la-liga",
    "Serie A": "serie-a",
    "Bundesliga": "bundesliga",
    "Ligue 1": "ligue-1",
}

TEAMS = {
    "Premier League": [
        ("Arsenal", "arsenal"), ("Manchester City", "manchester-city"),
        ("Liverpool", "liverpool"), ("Chelsea", "chelsea"),
        ("Manchester United", "manchester-united"),
        ("Tottenham Hotspur", "tottenham"), ("Newcastle United", "newcastle-united"),
        ("Aston Villa", "aston-villa"), ("Brighton", "brighton"),
        ("West Ham", "west-ham"), ("Everton", "everton"),
        ("Leicester City", "leicester-city"), ("Wolves", "wolves"),
        ("Crystal Palace", "crystal-palace"), ("Fulham", "fulham"),
    ],
    "La Liga": [
        ("Real Madrid", "real-madrid"), ("Barcelona", "barcelona"),
        ("Atletico Madrid", "atletico-madrid"), ("Sevilla", "sevilla"),
        ("Real Sociedad", "real-sociedad"), ("Athletic Bilbao", "athletic-bilbao"),
        ("Real Betis", "real-betis"), ("Villarreal", "villarreal"),
        ("Valencia", "valencia"), ("Girona", "girona"),
        ("Celta Vigo", "celta-vigo"), ("Osasuna", "osasuna"),
        ("Rayo Vallecano", "rayo-vallecano"), ("Getafe", "getafe"),
        ("Mallorca", "mallorca"),
    ],
    "Serie A": [
        ("Inter Milan", "inter"), ("AC Milan", "ac-milan"),
        ("Juventus", "juventus"), ("Napoli", "napoli"),
        ("Roma", "roma"), ("Lazio", "lazio"),
        ("Atalanta", "atalanta"), ("Fiorentina", "fiorentina"),
        ("Bologna", "bologna"), ("Torino", "torino"),
        ("Genoa", "genoa"), ("Udinese", "udinese"),
        ("Sassuolo", "sassuolo"), ("Empoli", "empoli"),
        ("Lecce", "lecce"),
    ],
    "Bundesliga": [
        ("Bayern Munich", "bayern-munich"), ("Borussia Dortmund", "borussia-dortmund"),
        ("RB Leipzig", "rb-leipzig"), ("Bayer Leverkusen", "bayer-leverkusen"),
        ("Eintracht Frankfurt", "eintracht-frankfurt"),
        ("VfB Stuttgart", "vfb-stuttgart"), ("Wolfsburg", "wolfsburg"),
        ("Freiburg", "freiburg"), ("Union Berlin", "union-berlin"),
        ("Mainz 05", "mainz"), ("Augsburg", "augsburg"),
        ("Werder Bremen", "werder-bremen"), ("Hoffenheim", "hoffenheim"),
        ("Borussia Monchengladbach", "borussia-monchengladbach"),
        ("Koln", "koln"),
    ],
    "Ligue 1": [
        ("Paris Saint-Germain", "psg"), ("Marseille", "marseille"),
        ("Lyon", "lyon"), ("Monaco", "monaco"),
        ("Lille", "lille"), ("Nice", "nice"),
        ("Rennes", "rennes"), ("Lens", "lens"),
        ("Strasbourg", "strasbourg"), ("Nantes", "nantes"),
        ("Montpellier", "montpellier"), ("Reims", "reims"),
        ("Toulouse", "toulouse"), ("Brest", "brest"),
        ("Le Havre", "le-havre"),
    ],
}

# ---------- Helpers ----------
def leagues_keyboard():
    kb = [[InlineKeyboardButton(f"⚽ {name}", callback_data=f"league:{name}")]
          for name in LEAGUES]
    return InlineKeyboardMarkup(kb)

def action_keyboard(league):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👕 I want to choose my team",
                              callback_data=f"choose_team:{league}")],
        [InlineKeyboardButton("📰 I want to read all news",
                              callback_data=f"all_news:{league}")],
        [InlineKeyboardButton("🔁 Change league", callback_data="change_league")],
    ])

def teams_keyboard(league):
    teams = TEAMS[league]
    rows, row = [], []
    for name, slug in teams:
        row.append(InlineKeyboardButton(name, callback_data=f"team:{league}:{slug}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"league:{league}")])
    return InlineKeyboardMarkup(rows)

def format_news(articles, header):
    if not articles:
        return f"{header}\n\n⚠️ No news available right now. Try again later."
    lines = [header, ""]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {a['title']}\n🔗 {a['url']}")
    return "\n\n".join(lines)

# ---------- Handlers ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    save_user(uid, USERS.get(str(uid), {}))

    welcome = (
        "🤖 *mikemod football bot is here!*\n"
        "Do you want to know about the top football tournaments and the best teams in the world?\n\n"
        "All the best from the top European leagues — news, stats, transfers, squads, "
        "match schedules & results, live standings and a fan menu. ⚽\n\n"
        "👉 *Choose the league you want to follow.*\n"
        "_You can always change settings later._"
    )
    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=leagues_keyboard()
    )

async def change_league(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "👉 Choose the league you want to follow:",
        reply_markup=leagues_keyboard(),
    )

async def league_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    league = q.data.split(":", 1)[1]
    user = USERS.get(str(q.from_user.id), {})
    user["league"] = league
    save_user(q.from_user.id, user)

    text = (
        f"✅ *{league}* selected!\n\n"
        "What would you like to do?"
    )
    await q.edit_message_text(
        text, parse_mode="Markdown", reply_markup=action_keyboard(league)
    )

async def all_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Fetching latest news…")
    league = q.data.split(":", 1)[1]
    await q.edit_message_text(f"📰 Fetching latest *{league}* news…", parse_mode="Markdown")
    articles = await fetch_league_news(league, limit=7)
    text = format_news(articles, f"📰 *Latest {league} News*")
    await q.edit_message_text(
        text, parse_mode="Markdown", reply_markup=action_keyboard(league),
        disable_web_page_preview=True,
    )

async def choose_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    league = q.data.split(":", 1)[1]
    await q.edit_message_text(
        f"👕 Choose your *{league}* team:",
        parse_mode="Markdown",
        reply_markup=teams_keyboard(league),
    )

async def team_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Loading team news…")
    _, league, slug = q.data.split(":", 2)
    team_name = next((n for n, s in TEAMS[league] if s == slug), slug)

    user = USERS.get(str(q.from_user.id), {})
    user["league"] = league
    user["team"] = team_name
    user["team_slug"] = slug
    save_user(q.from_user.id, user)

    articles = await fetch_team_news(slug, limit=3)
    body = format_news(articles, f"⚽ *{team_name}* — Latest News")
    body += "\n\n🔗 Read more: https://tribuna.com/"
    body += "\n\n_You'll now receive updates about this team every 15 minutes._"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Change team", callback_data=f"choose_team:{league}")],
        [InlineKeyboardButton("🏠 Main menu", callback_data="change_league")],
    ])
    await q.edit_message_text(
        body, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True
    )

# ---------- Background job: 15-minute updates ----------
async def send_team_updates(ctx: ContextTypes.DEFAULT_TYPE):
    for uid_str, data in list(USERS.items()):
        slug = data.get("team_slug")
        team = data.get("team")
        if not slug or not team:
            continue
        try:
            articles = await fetch_team_news(slug, limit=2)
            if not articles:
                continue
            msg = format_news(articles, f"⏰ *{team}* — Update")
            msg += "\n\n🔗 Read more: https://tribuna.com/"
            await ctx.bot.send_message(
                int(uid_str), msg, parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning(f"update failed for {uid_str}: {e}")
        await asyncio.sleep(0.5)  # be gentle to tribuna

async def post_init(app: Application):
    # schedule every 15 minutes
    app.job_queue.run_repeating(send_team_updates, interval=900, first=60)

def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("change", change_league))
    app.add_handler(CallbackQueryHandler(change_league, pattern="^change_league$"))
    app.add_handler(CallbackQueryHandler(league_selected, pattern="^league:"))
    app.add_handler(CallbackQueryHandler(all_news, pattern="^all_news:"))
    app.add_handler(CallbackQueryHandler(choose_team, pattern="^choose_team:"))
    app.add_handler(CallbackQueryHandler(team_selected, pattern="^team:"))

    logger.info("Bot started…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
