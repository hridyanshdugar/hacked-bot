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
        self.message_id = 1336237048696275007  # The ID of the message to watch for reactions
        self.role_to_add = None  # The role to assign when reacted to
        self.add_commands()
    
    async def on_ready(self):
        print(f'{self.user} has connected to {self.guilds[0].name}!')
        
        # Add slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(e)

        # Add reaction message to get participant assigned
        for guild in self.guilds:
            if guild.name == os.getenv("DISCORD_GUILD"):
                break
        self.role_to_add = discord.utils.get(guild.roles, name="participant")  # Get the role

        if self.role_to_add:
            print(f"Reaction role set! Role `{self.role_to_add.name}` will be added when users react to message ID `{self.message_id}`.")
        else:
            print(f"Role `participant` not found. Please check the role name.")
    
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Check if the reaction is on the specified message
        if payload.message_id == self.message_id:
            guild = self.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)

            # Check if the emoji is what you expect (e.g., ✅)
            if str(payload.emoji) == "✅":
                role = self.role_to_add
                if role:
                    await member.add_roles(role)
                    print(f"Added role {role.name} to {member.name}")
    
    def add_commands(self):
        @self.command(name="ping", description="lol")
        @commands.has_role("mod")
        async def ping(ctx):
            await ctx.send("pong")
        
        # @self.command(name="enableTeam")
        # async def enableTeam(ctx):
        #     self.tree.add_command(self.team, guild=discord.Object(ctx.guild.id))
        #     print("Team creation activated")
    
        @self.tree.command(name="team")
        # @self.tree.describe(team_name="The name of your team.")
        @app_commands.describe(member1="A team member.")
        @app_commands.describe(member2="A team member.")
        @app_commands.describe(member3="A team member.")
        @app_commands.describe(member4="A team member.")
        @app_commands.describe(member5="A team member.")
        async def team( 
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
                can_create_with_member = False
                for role in member.roles:
                    if role.name == "participant":
                        can_create_with_member =True
                        break

                if not can_create_with_member:
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
            team_role = await interaction.guild.create_role(name=team_name, mentionable=True, colour=discord.Colour.from_str("#adadad")) # team role

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
        
        @self.command(name="hitch", description="lol")
        @commands.has_role("mod")
        async def hitch(ctx):
            embed = discord.Embed(
                title="Introduction",
                description="Hi folks! This is HackED's official HitchHacker's Guide To The Galaxy. Contained in this channel is everything you'll need to get the most out of your hackathon experience, as well as the answers to a lot of questions you might have throughout the hackathon; it's a reference for safety information, the event schedule, project guidelines, submission instructions, and more.\n Please use the search function or the links provided to navigate the Guide (and, if you have any questions that aren't answered, ask us in <#1336202563548086301>!",
                color=62441  # You can use any color here
            )
            await ctx.send(embed=embed)

            embed = discord.Embed(
                title="`Health & Safety Information`",
                description="- HackED has absolutely zero tolerance for sexual harassment or misconduct. Any form of this behavior could result in expulsion from the event and a follow-up with the Office of the Dean.\n - HackED has absolutely zero tolerance for violence or threats to other participants.\n\n ### `Transit`\n - For your safety, participants are **strongly discouraged from leaving the event in the middle of the night**.\n- This is not an overnight event, the event area will close at 10 PM each night, please coordinate a safe ride home.\n- Edmonton public transit routes stop running at some point during the night. If you do plan to take transit home late at night, please **make sure your route is still running**. More information about exact times for individual routes can be found [here](https://www.edmonton.ca/sites/default/files/public-files/assets/transit/ETS-Route-Frequency-Table-Sept-2023.pdf).\n- The University of Alberta's Safewalk program will not be running during the event, as it is a weekend.\n - For a safe ride home, dial #TAXI on your cell phone.\n\n ### `Food & Drink`\n- HackED aims to promote healthy work habits and environments. We ask participants to **prioritize their own mental and physical health** as much as possible, above hackathon participation or projects.\n- Staying well-fed and hydrated are important! Please take time to eat and drink water throughout the event.\n- We will provide **snacks** throughout the event and **dinner** on Saturday and Sunday.\n- There is a water fountain available at our in-person location on DICE 8F. \n- Participants are also encouraged to bring what they need to eat for as long as they plan to stay on-campus.",
                color=62441
            )

            await ctx.send(embed=embed)

            embed = discord.Embed(
                title="`Leaving & Reentering The Building`",
                description="- If you leave and reenter the building, **you must sign out and back in at the front desk.**\n- Elevators in this building require a key-pass after hours. If you get stuck downstairs and aren't able to use the elevators, send a message in <#1339085635310452746> and a volunteer will let you in.\n- It is possible to get locked in the stairwell near the water fountain. If that happens, send a message in <#1339085635310452746> and a volunteer will let you in.",
                color=62441
            )

            await ctx.send(embed=embed)

            embed = discord.Embed(
                title="`Housekeeping`",
                description="- Keep the area clean!\n- There are washrooms near the front desk.\n- A map of gender-neutral washrooms on campus can be found [here](https://www.ualberta.ca/maps.html?l=53.52805170773808,-113.52846739613842&z=18&campus=north_campus&c=All-Gender%20Washrooms). There are several on the first and second floors of the building.",
                color=62441
            )

            await ctx.send(embed=embed)

            embed = discord.Embed(
                title="`Workshops`",
                description="Throughout HackED we will be hosting a variety of awesome workshops where you can learn new skills that might be helpful for your project (and for career development and personal projects outside the hackathon!) The workshops will be run by our sponsor representatives and industry professionals.\nYou can check out the workshop schedule in the Events of this Discord server, or in <#1336202563011477559>. Announcements and information about each workshop (e.g. where to find it) will be sent out shortly before each workshop!",
                color=62441
            )

            await ctx.send(embed=embed)


            embed = discord.Embed(
                title="`Team Creation Details`",
                description="To create a team, run the /team command in <#1336202563548086300>. \n- Teams may have anywhere from 1 to 5 people (inclusive), and may consist of any combination of in-person and virtual participants.\n- The team you create on Discord is our official record of your team's participants and is what we will use for prize distribution.\n- If you want to add/remove someone to/from your team, please ping <@1264055395454816256>.",
                color=62441
            )

            await ctx.send(embed=embed)

            embed = discord.Embed(
                title="`Judging Signup Details`",
                description="### Signup \n Run the /judging command to signup after the signup time starts. More information on this will be found in <#1336202563011477557>.",
                color=62441
            )

            await ctx.send(embed=embed)
        
        @self.command(name="clear", description="lol")
        @commands.has_role("mod")
        async def clear(ctx):
            """Clears all messages in the channel."""
            await ctx.channel.purge()

        @self.tree.command(name="judging")
        # @self.tree.describe(team_name="The name of your team.")
        @app_commands.describe(member1="A team member.")
        @app_commands.describe(member2="A team member.")
        @app_commands.describe(member3="A team member.")
        @app_commands.describe(member4="A team member.")
        @app_commands.describe(member5="A team member.")
        @app_commands.describe(devpost="The link to the devpost")
        @app_commands.describe(github="The link to the github")
        async def judging( 
            interaction: discord.Interaction, 
            team_name: str,
            member1: discord.Member,
            member2: Optional[discord.Member],
            member3: Optional[discord.Member],
            member4: Optional[discord.Member],
            member5: Optional[discord.Member],
            devpost: str,
            github: str
        ):
            pass

