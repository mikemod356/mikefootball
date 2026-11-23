
import os
import logging
import inspect
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from news_fetcher import fetch_league_news, fetch_team_news


# ---------------- CONFIGURATION ----------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Add it to Railway Variables.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ---------------- LEAGUES AND TEAMS ----------------

LEAGUES = {
    "premier": {
        "name": "Premier League",
        "teams": [
            "Arsenal",
            "Chelsea",
            "Liverpool",
            "Manchester City",
            "Manchester United",
            "Tottenham",
            "Newcastle United",
            "Aston Villa",
            "Everton",
            "West Ham",
        ],
    },
    "laliga": {
        "name": "La Liga",
        "teams": [
            "Real Madrid",
            "Barcelona",
            "Atletico Madrid",
            "Sevilla",
            "Valencia",
            "Real Sociedad",
            "Villarreal",
            "Athletic Bilbao",
        ],
    },
    "seriea": {
        "name": "Serie A",
        "teams": [
            "Inter Milan",
            "AC Milan",
            "Juventus",
            "Napoli",
            "Roma",
            "Lazio",
            "Atalanta",
            "Fiorentina",
        ],
    },
    "bundesliga": {
        "name": "Bundesliga",
        "teams": [
            "Bayern Munich",
            "Borussia Dortmund",
            "Bayer Leverkusen",
            "RB Leipzig",
            "Eintracht Frankfurt",
            "Stuttgart",
        ],
    },
    "ligue1": {
        "name": "Ligue 1",
        "teams": [
            "PSG",
            "Marseille",
            "Monaco",
            "Lyon",
            "Lille",
            "Nice",
        ],
    },
}


# ---------------- HELPER FUNCTIONS ----------------

async def get_news(function, argument):
    """Support both synchronous and asynchronous news fetchers."""
    result = function(argument)

    if inspect.isawaitable(result):
        result = await result

    return result


def format_news(news):
    """Convert different news result formats into readable text."""

    if news is None:
        return "No news is available at the moment."

    if isinstance(news, str):
        return news.strip() or "No news is available at the moment."

    if isinstance(news, dict):
        title = news.get("title", "Football News")
        description = news.get("description", "")
        link = news.get("link") or news.get("url", "")

        message = f"⚽ {title}"

        if description:
            message += f"\n\n{description}"

        if link:
            message += f"\n\n🔗 {link}"

        return message

    if isinstance(news, (list, tuple)):
        if not news:
            return "No news is available at the moment."

        messages = []

        for index, item in enumerate(news, start=1):
            if isinstance(item, dict):
                title = item.get("title", "Football News")
                description = item.get("description", "")
                link = item.get("link") or item.get("url", "")

                item_text = f"{index}. ⚽ {title}"

                if description:
                    item_text += f"\n{description}"

                if link:
                    item_text += f"\n🔗 {link}"

                messages.append(item_text)

            else:
                messages.append(f"{index}. ⚽ {str(item)}")

        return "\n\n".join(messages)

    return str(news)


async def send_long_message(message, text):
    """Telegram messages cannot exceed 4096 characters."""

    text = str(text)

    if not text:
        text = "No news is available at the moment."

    for start in range(0, len(text), 4000):
        await message.reply_text(text[start:start + 4000])


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📰 All Football News", callback_data="all_news")
        ],
        [
            InlineKeyboardButton("🏆 Choose League", callback_data="choose_league")
        ],
        [
            InlineKeyboardButton("⚽ Follow a Team", callback_data="choose_team")
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def league_menu():
    keyboard = []

    for key, league in LEAGUES.items():
        keyboard.append([
            InlineKeyboardButton(
                league["name"],
                callback_data=f"league:{key}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def team_menu(league_key):
    league = LEAGUES[league_key]
    keyboard = []

    for team in league["teams"]:
        keyboard.append([
            InlineKeyboardButton(
                team,
                callback_data=f"team:{team}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Choose Another League",
                             callback_data="choose_league")
    ])

    return InlineKeyboardMarkup(keyboard)


# ---------------- START COMMAND ----------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    welcome = (
        "⚽ Welcome to Football News Bot!\n\n"
        "Get football news from your favourite leagues and teams.\n\n"
        "Choose what you want below:"
    )

    await update.message.reply_text(
        welcome,
        reply_markup=main_menu(),
    )


# ---------------- SHOW LEAGUES ----------------

async def change_league(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🏆 Select a football league:",
        reply_markup=league_menu(),
    )


async def choose_team(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🏆 First, select the league:",
        reply_markup=league_menu(),
    )


# ---------------- CALLBACK HANDLER ----------------

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    data = query.data

    try:

        if data == "main_menu":
            await query.edit_message_text(
                "⚽ Football News Bot\n\nChoose an option:",
                reply_markup=main_menu(),
            )
            return

        if data == "choose_league":
            await query.edit_message_text(
                "🏆 Select a football league:",
                reply_markup=league_menu(),
            )
            return

        if data == "choose_team":
            await query.edit_message_text(
                "🏆 Select a league to see its teams:",
                reply_markup=league_menu(),
            )
            return

        if data.startswith("league:"):
            league_key = data.split(":", 1)[1]

            if league_key not in LEAGUES:
                await query.message.reply_text("Invalid league selected.")
                return

            league_name = LEAGUES[league_key]["name"]

            await query.edit_message_text(
                f"🏆 {league_name}\n\nWhat would you like to do?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "📰 Get League News",
                            callback_data=f"league_news:{league_key}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⚽ Select a Team",
                            callback_data=f"teams:{league_key}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Main Menu",
                            callback_data="main_menu",
                        )
                    ],
                ]),
            )
            return

        if data.startswith("teams:"):
            league_key = data.split(":", 1)[1]

            if league_key not in LEAGUES:
                await query.message.reply_text("Invalid league selected.")
                return

            await query.edit_message_text(
                f"⚽ Select a team from {LEAGUES[league_key]['name']}:",
                reply_markup=team_menu(league_key),
            )
            return

        if data.startswith("league_news:"):
            league_key = data.split(":", 1)[1]

            if league_key not in LEAGUES:
                await query.message.reply_text("Invalid league.")
                return

            league_name = LEAGUES[league_key]["name"]

            status = await query.message.reply_text(
                f"⏳ Fetching {league_name} news..."
            )

            try:
                news = await get_news(
                    fetch_league_news,
                    league_name,
                )

                result = format_news(news)

                await send_long_message(
                    query.message,
                    f"📰 {league_name} News\n\n{result}",
                )

            except Exception:
                logger.exception("League news error")

                await query.message.reply_text(
                    "Sorry, I couldn't fetch the news right now. "
                    "Please try again later."
                )

            finally:
                try:
                    await status.delete()
                except Exception:
                    pass

            return

        if data.startswith("team:"):
            team_name = data.split(":", 1)[1]

            status = await query.message.reply_text(
                f"⏳ Fetching news about {team_name}..."
            )

            try:
                news = await get_news(
                    fetch_team_news,
                    team_name,
                )

                result = format_news(news)

                await send_long_message(
                    query.message,
                    f"⚽ {team_name} News\n\n{result}",
                )

            except Exception:
                logger.exception("Team news error")

                await query.message.reply_text(
                    "Sorry, I couldn't fetch this team's news. "
                    "Please try again later."
                )

            finally:
                try:
                    await status.delete()
                except Exception:
                    pass

            return

        if data == "all_news":
            status = await query.message.reply_text(
                "⏳ Fetching football news. Please wait..."
            )

            try:
                for key, league in LEAGUES.items():
                    try:
                        news = await get_news(
                            fetch_league_news,
                            league["name"],
                        )

                        result = format_news(news)

                        await send_long_message(
                            query.message,
                            f"📰 {league['name']}\n\n{result}",
                        )

                    except Exception:
                        logger.exception(
                            "Error fetching %s news",
                            league["name"],
                        )

                        await query.message.reply_text(
                            f"Could not fetch {league['name']} news."
                        )

            finally:
                try:
                    await status.delete()
                except Exception:
                    pass

            return

    except Exception:
        logger.exception("Button handler error")

        await query.message.reply_text(
            "Something went wrong. Please try again."
        )


# ---------------- TEXT MESSAGE HANDLER ----------------

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Please use the buttons below to navigate the bot.",
        reply_markup=main_menu(),
    )


# ---------------- ERROR HANDLER ----------------

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "An error occurred while processing an update:",
        exc_info=context.error,
    )


# ---------------- MAIN FUNCTION ----------------

def main():

    print("Starting Football News Bot...")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("change", change_league)
    )

    application.add_handler(
        CommandHandler("team", choose_team)
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    # Text messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    # Error handling
    application.add_error_handler(error_handler)

    print("Bot is running successfully!")

    # No JobQueue or post_init is used in this version.
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
