import re
from typing import Any, Optional, Type, List
import discord
from discord.app_commands.installs import AppCommandContext, AppInstallationType
from discord.app_commands.tree import CommandTree
from discord.ext import commands
from discord.ext.commands.bot import _default
from discord.utils import MISSING
import discord.utils
from discord import app_commands
import logging
from discord.utils import get as dget
import os
from .utils import get_confirmation

class Bot(commands.Bot):
    def __init__(self, command_prefix="~") -> None:
        super().__init__(command_prefix=command_prefix, intents=discord.Intents.all())
        self.add_commands()
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
    
    def add_commands(self):
        @self.command(name="ping", description="lol")
        async def ping(ctx):
            await ctx.send("pong")
        
        @self.command(name="enableTeam")
        async def enableTeam(ctx):
            self.tree.add_command(self.team, guild=discord.Object(ctx.guild.id))
            logging("Team creation activated")
    
    @app_commands.command()
    @app_commands.describe(team_name="The name of your team.")
    @app_commands.describe(member1="A team member.")
    @app_commands.describe(member2="A team member.")
    @app_commands.describe(member3="A team member.")
    @app_commands.describe(member4="A team member.")
    @app_commands.describe(member5="A team member.")
    async def team(
        self, 
        interaction: discord.Interaction, 
        team_name: str,
        member1: discord.Member,
        member2: Optional[discord.Member],
        member3: Optional[discord.Member],
        member4: Optional[discord.Member],
        member5: Optional[discord.Member]
    ):
        '''
        Create a team.
        '''

        members = [m for m in [member1, member2, member3, member4, member5] if m != None]
        logging.info(f"team called with args: team_name={team_name}, members={[m.name for m in members]}")

        # check permissions
        override = False

        if not override:
            
            # if team creation disabled, exit
            interaction.client.cogs # for some reason, i can only access Teams cog once this has been run.
            team_cog = interaction.client.get_cog("Teams")

            if not os.getenv("TEAM_CREATION_ENABLED"):
                logging.info(f"team: ignoring because team creation is disabled")
                await interaction.response.send_message(f"❌ Your team was not created; team creation is disabled right now.")
                return

            # check run in correct channel
            if not interaction.channel.name == "team-create":
                logging.info(f"team: ignoring because run in wrong channel")
                await interaction.response.send_message(f"❌ Your team was not created; you cannot run this command here.")
                return
        
        # ===== check team name
        
        # check length of name
        if len(team_name) > 100:
            await interaction.response.send_message(f"❌ Your team was not created; your team name is too long. The maximum team name length is 100 characters.")
            return

        # check validity of name
        valid_text_channel = "^([a-z0-9]+-)*[a-z0-9]+$" # valid regex match to something that can be a discord text channel
        if not re.search(valid_text_channel, team_name):
            await interaction.response.send_message(f"❌ Your team was not created; your team name is invalid. Team names may only consist of **lowercase letters** and **digits** separated by **dashes**.\nA few examples of valid team names: `some-team`, `hackathon-winners`, `a-b-c-d-e-f`")
            return
        
        # ensure team name not already taken
        if dget(interaction.guild.channels, name=team_name):
            await interaction.response.send_message(f"❌ Your team was not created; there is already a team called `{team_name}`.")
            return
        
        # ensure team name won't cause conflicts with anything already in the server
        if dget(interaction.guild.channels, name=team_name) \
            or dget(interaction.guild.categories, name=team_name) \
            or dget(interaction.guild.channels, name=team_name) \
            or dget(interaction.guild.roles, name=team_name):

            await interaction.response.send_message(f"❌ Your team was not created; the name `{team_name}` is not allowed.")
            return
        
        # ===== check team members
        
        # get unique mentions of users for the team members
        for member in members:

            # already disincludes role mentions, need to disinclude bots
            if member.bot:
                await interaction.response.send_message(f"❌ Your team was not created; you cannot have a bot on your team.")
                return

            # ensure user not already in team
            if len(member.roles) > 2:
                await interaction.response.send_message(f"❌ Your team was not created; at least one member is already in a team.")
                return
            
            # ensure user is a participant
            for role in member.roles:
                if role.id == "participant":
                    break
                else:
                    await interaction.response.send_message(f"❌ Your team was not created; at least one member does not have the `@participant` role.")
                    return
            
        # check for empty team
        if members == []:
            await interaction.response.send_message(f"❌ Your team was not created; you cannot have an empty team!")
            return
        
        # ensure sender is on the team
        if interaction.user not in members and not override: # organizer can create team without restriction
            await interaction.response.send_message(f"❌ Your team was not created; you cannot create a team that you yourself are not on. (Ensure that you are one of the 5 users mentioned in one of the 'member' fields.)")
            return
            
        # ===== team can be created

        msg = "`[Command is being run in override mode.]`" if override else ""
        msg += f"The team `{team_name}` will be created, and members {' '.join([m.mention for m in members])} will be added.\n\n{interaction.user.mention}, please react to this message with ✅ to confirm, or ❌ to cancel."

        await interaction.response.send_message(msg)
        confirm_msg = await interaction.original_response()
        confirmed = await get_confirmation(interaction.client, interaction.user, confirm_msg)

        if confirmed == None: # timed out
            return
        elif confirmed == False: # reacted with ❌
            await confirm_msg.reply(f"Team {team_name} was not created.")
            return
        # otherwise, user confirmed, so we can proceed

        # create team category & role
        team_cat = await interaction.guild.create_category(name=team_name) # category to store team text & vc
        team_role = await interaction.guild.create_role(name=team_name, mentionable=True, colour="#adadad") # team role

        # Privatize category so that only team and some others can view
        await team_cat.set_permissions(interaction.guild.default_role, read_messages=False) # @everyone can't view
        await team_cat.set_permissions(team_role, read_messages=True)
        for role_name in ['organizer', 'mentor', 'volunteer', 'sponsor', 'judge']:
            await team_cat.set_permissions(
                dget(interaction.guild.roles, name=role_name), # get role with ID identified in config
                read_messages=True
            )

        # Create the text and voice channel
        team_text = await interaction.guild.create_text_channel(name=team_name, category=team_cat)
        team_vc = await interaction.guild.create_voice_channel(name=team_name, category=team_cat)
        
        # Add created role to all team members
        for member in members:
            await member.add_roles(team_role)

        # React in confirmation and send notification in team text channel
        await team_text.send(f'Hey {" ".join([member.mention for member in members])}! Here is your team category & channels.')

        logging.info(f"Team created: {team_name}, {[m.name for m in members]}, {team_role}")

