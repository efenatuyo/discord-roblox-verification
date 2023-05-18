import requests
import json
import random
import discord
import datetime
import asyncio
class verifyBot:
    class DotDict(dict):
        def __getattr__(self, attr):
            if attr in self:
                return self[attr]
            else:
                return None
            
    def __init__(self):
        self.config = self._config
        self.prefix = self.config.get('discord_bot', {}).get('prefix')
        self.token = self.config.get('discord_bot', {}).get("token")
        self.role_id = self.config.get('discord_bot', {}).get('verify_role_id')
        assert self.prefix or self.token or self.role_id, "Missing arguments"
        self.running = []

    
    @property
    def _config(self):
        with open("config.json", "r") as f: return json.load(f)

    def description(self, user_id):
        response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
        if response.status_code == 404:
            return False
        return (response.json())['description']
        
    def generate_verify_text(self):
        words = ["funny", "haha", "developer", "safe", "verify", "manager", "cow", "work", "plane", "development", "eyes", "build", "pop", "dog", "cow", "quality", "jelly"]
        random_words = random.sample(words, random.randint(10, 17))
        sentence = " ".join(random_words)
        return sentence
    
    def add_database(self, discord_id, roblox_id):
        self.config['loaded_accounts'][discord_id] = roblox_id
        with open("config.json", "w") as f: json.dump(self.config, f, indent=4)
        return verifyBot.DotDict({"success": True})
    
    def verify(self, discord_id):
        if discord_id in self.config['loaded_accounts']: return verifyBot.DotDict({"verification_required": False, "roblox_id": self.config['loaded_accounts'][discord_id]})
        else: return verifyBot.DotDict({"verification_required": True, "verification_text": self.generate_verify_text()})
    
    def run_bot(self):
        bot = discord.Bot(intents=discord.Intents.all())
        
        @bot.event
        async def on_ready():
            print("Bot is online")
        
        class MyView(discord.ui.View):
            cooldown_duration = 10
            def __init__(self, roblox_id, verify_text, role_id, ctx):
                super().__init__()
                self.roblox_id = roblox_id
                self.verify_text = verify_text
                self.role_id = role_id
                self.ctx = ctx
                self.last_click = {}
            
            async def on_timeout(g):
                for child in g.children:
                    child.disabled = True
                    if g.ctx.author.id in self.running: self.running.remove(g.ctx.author.id)
                    await g.message.edit(content="Invalid Roblox Id", view=None)
                    
            @discord.ui.button(label="Click me if verifed!", style=discord.ButtonStyle.primary)
            async def button_callback(g, button, interaction):
                user_id = interaction.user.id
                
                if user_id in g.last_click:
                    last_click_time = g.last_click[user_id]
                    current_time = datetime.datetime.now()
                    elapsed_time = (current_time - last_click_time).total_seconds()

                    if elapsed_time < g.cooldown_duration:
                        remaining_time = g.cooldown_duration - elapsed_time
                        return await interaction.response.send_message(f"Cooldown still active. Please wait {remaining_time:.1f} seconds.")
                
                guild = g.ctx.guild
                g.last_click[user_id] = datetime.datetime.now()    
                verify_text = g.verify_text
                description = self.description(g.roblox_id)
                if not description: return await g.on_timeout()
                if description == verify_text:
                    self.add_database(user_id, g.roblox_id)
                    member = guild.get_member(user_id)
                    await member.add_roles(g.role_id)
                    await interaction.response.send_message("Verifed you now have access to the server.") 
                else: await interaction.response.send_message("Invalid Description")

        @bot.slash_command(description="verify globally")
        async def verify(ctx, roblox_id: discord.Option(str, description="roblox user id")):
            if ctx.guild is None:
                return await ctx.respond("You are only allowed to run this in guilds", ephemeral=True)
            
            if ctx.author.id in self.running:
                return await ctx.respond("You are already have a pending verification", ephemeral=True)

            if not self.verify(str(ctx.author.id)).verification_required:
                return await ctx.respond("You are already verifed", ephemeral=True)
            
            self.running.append(ctx.author.id)
            await ctx.respond("starting verify", ephemeral=True)
            role = discord.utils.get(ctx.guild.roles, id=int(self.role_id))
            verfy_text = self.generate_verify_text()
            message = await ctx.author.send(f"Put this text into your roblox bio ```{verfy_text}```", view=MyView(roblox_id=roblox_id, verify_text=verfy_text, role_id=role, ctx=ctx))
            timeout_duration = 60
            await asyncio.sleep(timeout_duration)
            await message.edit("timed out", view=None)
            if ctx.author.id in self.running: self.running.remove(ctx.author.id)
            
        
        @bot.event
        async def on_member_join(member):
            role = discord.utils.get(member.guild.roles, id=int(self.role_id))
            if (self.verify(str(member.id))).verification_required:
                await member.send("Type !verify in guild to verify")
                pass
            else:
                await member.add_roles(role)
                return await member.send("Verifed!")
        
        bot.run(self.token)
    
verifyBot().run_bot()