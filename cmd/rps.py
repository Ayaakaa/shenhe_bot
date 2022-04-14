import random as rand
import discord
import getpass
owner = getpass.getuser()
import sys 
sys.path.append(f'C:/Users/{owner}/shenhe_bot/asset')
import global_vars
from discord.ext import commands
with open(f'C:/Users/{owner}/shenhe_bot/asset/flow.yaml', encoding = 'utf-8') as file:
    users = yaml.full_load(file)

class RPSCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    reactions = ['✊', '🖐️', '✌️']

    @commands.command()
    async def rps(self, ctx):
        embed = global_vars.defaultEmbed("剪刀石頭布vs申鶴", "「選擇下方的一個手勢吧...」")
        global_vars.setFooter(embed)
        msg = await ctx.send(embed=embed)
        for reaction in self.reactions: await msg.add_reaction(reaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, ev: discord.RawReactionActionEvent):
        if ev.user_id != self.bot.user.id:
            await self.bot.http.delete_message(ev.channel_id, ev.message_id)
            msg = "「我輸了嗎...?」 :anger:" if str(ev.emoji) == rand.choice(self.reactions) \
                else "「這個叫做剪刀石頭布的遊戲好像挺好玩...」"
            embed = global_vars.defaultEmbed("誰贏了呢?", f"{msg}\n你出了: {str(ev.emoji)}\n申鶴出了: {rand.choice(self.reactions)}")
            global_vars.setFooter(embed)
            await self.bot.get_channel(ev.channel_id).send(embed=embed)
            for user in users:
                dateNow = datetime.datetime.now()
                if 'rps' not in user:
                    user['rps'] = 1
                if 'rpsDate' not in user:
                    user['rpsDate'] = dateNow
                diffDays = abs((dateNow - user['rpsDate']).days)
                if diffDays >= 1 and user['rps']<= 10:
                    user['flow'] += 1
                    user['rps'] += 1
                    with open(f'C:/Users/{owner}/shenhe_bot/asset/flow.yaml', 'w', encoding = 'utf-8') as file:
                    yaml.dump(users, file)

def setup(bot: commands.Bot):
    bot.add_cog(RPSCog(bot))