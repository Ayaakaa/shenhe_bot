from discord.ext.forms import Form
from discord.ext import commands
import yaml
from cmd.asset.global_vars import defaultEmbed, setFooter
import uuid

with open(f'cmd/asset/flow.yaml', encoding='utf-8') as file:
    users = yaml.full_load(file)
with open(f'cmd/asset/bank.yaml', encoding='utf-8') as file:
    bank = yaml.full_load(file)
with open(f'cmd/asset/shop.yaml', encoding='utf-8') as file:
    shop = yaml.full_load(file)
with open(f'cmd/asset/log.yaml', encoding='utf-8') as file:
    logs = yaml.full_load(file)


class FlowShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def shop(self, ctx):
        if ctx.invoked_subcommand is None:
            itemStr = ""
            count = 1
            for item in shop:
                itemID = item
                itemStr = itemStr + \
                    f"{count}. {shop[itemID]['name']} - {shop[itemID]['flow']} flow ({shop[itemID]['current']}/{shop[itemID]['max']})\n||{shop[itemID]['uuid']}||\n"
                count += 1
            embed = defaultEmbed("🛒 flow商店", itemStr)
            setFooter(embed)
            await ctx.send(embed=embed)

    @shop.command()
    @commands.has_role("小雪團隊")
    async def newitem(self, ctx):
        form = Form(ctx, '新增商品', cleanup=True)
        form.add_question('商品名稱?', 'name')
        form.add_question('flow幣價格?', 'flow')
        form.add_question('最大購買次數?', 'max')
        form.edit_and_delete(True)
        form.set_timeout(60)
        await form.set_color("0xa68bd3")
        result = await form.start()
        uuid = str(uuid.uuid1())
        shop[uuid] = {'name': result.name, 'flow': int(
            result.flow), 'current': 0, 'max': int(result.max)}
        with open(f'cmd/asset/shop.yaml', 'w', encoding='utf-8') as file:
            yaml.dump(shop, file)
        await ctx.send(f"商品{result.name}新增成功")

    @shop.command()
    @commands.has_role("小雪團隊")
    async def removeitem(self, ctx, uuid):
        if uuid in shop:
            del shop[uuid]
            with open(f'cmd/asset/shop.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(shop, file)
            await ctx.send("商品刪除成功")

    @shop.command()
    async def buy(self, ctx):
        itemStr = ""
        count = 1
        for item in shop:
            uuid = item
            itemStr = itemStr + \
                f"{count}. {shop[uuid]['name']} - {shop[uuid]['flow']} flow ({shop[uuid]['current']}/{shop[uuid]['max']})\n"
            count += 1
        form = Form(ctx, '要購買什麼商品?(輸入數字)', cleanup=True)
        form.add_question(f'{itemStr}', 'number')
        form.edit_and_delete(True)
        form.set_timeout(60)
        await form.set_color("0xa68bd3")
        result = await form.start()
        shopList = list(shop.items())
        pos = int(result.number) - 1
        discordID = ctx.author.id
        if discordID in users:
            itemPrice = int(shopList[pos][1]['flow'])
            if users[discordID]['flow'] < itemPrice:
                await ctx.send(f"{ctx.author.mention} 你的flow幣不足夠購買這項商品")
                return
            if shop[pos]['current'] >= shop[pos]['max']:
                await ctx.send(f"{ctx.author.mention} 這個商品已經售罄了")
                return

            shop[pos][1]['current'] += 1
            with open(f'cmd/asset/shop.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(shop, file)
            logID = str(uuid.uuid1())
            logs[logID] = {'item': shop[pos][1]['name'], 'flow': itemPrice,
                           'buyerID': ctx.author.id, 'itemUUID': shop[pos][1]['uuid']}
            with open(f'cmd/asset/log.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(logs, file)
            users[discordID]['flow'] -= itemPrice
            bank['flow'] += itemPrice
            with open(f'cmd/asset/bank.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(bank, file)
            with open(f'cmd/asset/flow.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(users, file)
            await ctx.send(f"商品 {shop[pos][1]['name']} 購買成功, 詳情請查看私訊")
            await ctx.author.send(f"您已在flow商城購買了 {shop[1][pos]['name']} 商品, 請將下方的收據截圖並寄給小雪或律律來兌換商品")
            embed = defaultEmbed(
                "📜 購買證明", f"購買人: {ctx.author.mention}\n購買人ID: {ctx.author.id}\n商品: {shop[pos]['name']}\nUUID: {shop[pos]['uuid']}\n價格: {shop[pos]['flow']}")
            setFooter(embed)
            await ctx.author.send(embed=embed)
        else:
            discordID = ctx.author.id
            user = self.bot.get_user(discordID)
            flowCog = self.bot.get_cog('FlowCog')
            await flowCog.register(ctx, user, discordID)

    @shop.command()
    @commands.has_role("小雪團隊")
    async def log(self, ctx):
        for log in logs:
            logID = log
            user = self.bot.get_user(logs[logID]['buyerID'])
            embed = defaultEmbed(
                "購買紀錄", f"商品: {logs[logID]['item']}\n價格: {logs[logID]['flow']}\n購買人: {user.mention}\n購買人ID: {logs[logID]['buyerID']}\n商品UUID: {logs[logID]['itemUUID']}")
            setFooter(embed)
            await ctx.send(embed=embed)

    @shop.command()
    @commands.has_role("小雪團隊")
    async def clear(self, ctx, uuid):
        if uuid == "all":
            for item in shop:
                itemID = item
                shop[itemID]['current'] = 0
                with open(f'cmd/asset/shop.yaml', 'w', encoding='utf-8') as file:
                    yaml.dump(shop, file)
            await ctx.send(f"已將所有商品的購買次數清零")
            return
        elif int(uuid) in shop:
            del shop[uuid]


def setup(bot):
    bot.add_cog(FlowShopCog(bot))
