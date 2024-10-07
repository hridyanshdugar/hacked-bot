import discord
import asyncio
from discord.ext import commands

async def get_confirmation(bot: commands.Bot, confirm_user: discord.User, confirm_msg: discord.Message):
    '''
    Waits for `confirm_user` to react to `confirm_message`.
    If the user reacts with ✅, it returns True.
    If the user reacts with ❌, it returns False.
    If the program times out (after 20s), it returns None.
    '''

    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    # TODO: consider char limit

    def check(reaction, user):
        return user == confirm_user and reaction.emoji in ["✅", "❌"]

    # waiting for reaction confirmation
    try:
        reaction, user = await bot.wait_for('reaction_add', check=check, timeout=20.0) # 20 second timeout
    except asyncio.TimeoutError:
        await confirm_msg.reply("Timed out waiting for confirmation; please rerun the command if you want to try again.")
        return None

    if reaction.emoji == "✅":
        return True
    else:
        return False
    