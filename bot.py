

async def choose_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    league = query.data.split(":", 1)[1]
    if league not in TEAMS:
        await query.edit_message_text("Sorry, that league was not found. Send /start.")
        return

    await query.edit_message_text(
        f"👕 Choose your {league} team:",
        reply_markup=teams_keyboard(league),
    )


async def team_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Loading team news...")

    try:
        _, league, slug = query.data.split(":", 2)
        if league not in TEAMS:
            raise ValueError("Unknown league")

        team_name = next(
            (name for name, team_slug in TEAMS[league] if team_slug == slug),
            slug,
        )

        user_data = USERS.get(str(query.from_user.id), {})
        user_data["league"] = league
        user_data["team"] = team_name
        user_data["team_slug"] = slug
        save_user(query.from_user.id, user_data)

        articles = await fetch_team_news(slug, limit=3)
        message = format_news(articles, f"⚽ {team_name} — Latest News")
        message += "\n\nUse /start to return to the main menu."

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔁 Change team",
                callback_data=f"choose_team:{league}",
            )],
            [InlineKeyboardButton(
                "🏠 Main menu",
                callback_data="change_league",
            )],
        ])

        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    except Exception:
        logger.exception("Could not load team news")
        await query.edit_message_text(
            "Sorry, I couldn't load this team's news. Please try again.",
            reply_markup=leagues_keyboard(),
        )


# -------------------- ERROR HANDLER --------------------

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception("An error occurred while processing an update:", exc_info=context.error)


# -------------------- START BOT --------------------

def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is missing. Add BOT_TOKEN to Railway Variables."
        )

    # No JobQueue is used in this basic version.
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("change", change_command))

    app.add_handler(
        CallbackQueryHandler(change_league, pattern=r"^change_league$")
    )
    app.add_handler(
        CallbackQueryHandler(league_selected, pattern=r"^league:")
    )
    app.add_handler(
        CallbackQueryHandler(all_news, pattern=r"^all_news:")
    )
    app.add_handler(
        CallbackQueryHandler(choose_team, pattern=r"^choose_team:")
    )
    app.add_handler(
        CallbackQueryHandler(team_selected, pattern=r"^team:")
    )

    # Reply when a user sends ordinary text instead of a command.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_normal_message,
        )
    )

    app.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
