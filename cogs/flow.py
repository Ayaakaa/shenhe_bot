import uuid
from datetime import datetime, timedelta
from typing import Any, List

import aiosqlite
import discord
from dateutil import parser
from discord import Button, Interaction, Member, SelectOption, app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
from discord.ui import Select, View
from utility.FlowApp import FlowApp
from utility.GeneralPaginator import GeneralPaginator
from utility.utils import defaultEmbed, errEmbed, log

global debug_toggle
debug_toggle = False


class FlowCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.flow_app = FlowApp(self.bot.db)
        self.remove_flow_acc.start()

    def cog_unload(self) -> None:
        self.remove_flow_acc.cancel()

    @tasks.loop(hours=168)
    async def remove_flow_acc(self):
        print(log(True, False, 'Remove Flow Acc', 'task start'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT user_id, last_trans FROM flow_accounts')
        result = await c.fetchall()
        now = datetime.now()
        for index, tuple in enumerate(result):
            delta = now-parser.parse(tuple[1])
            if delta.days > 7:
                flow = await self.flow_app.get_user_flow(tuple[0])
                await self.flow_app.transaction(
                    tuple[0], flow, is_removing_account=True)
        print(log(True, False, 'Remove Flow Acc', 'task finished'))

    @remove_flow_acc.before_loop
    async def before_loop(self):
        now = datetime.now().astimezone()
        next_run = now.replace(hour=1, minute=30, second=0)  # 等待到早上1點30
        if next_run < now:
            next_run += timedelta(days=1)
        await discord.utils.sleep_until(next_run)

    @commands.Cog.listener()
    async def on_message(self, message):
        user_id = message.author.id
        user = self.bot.get_user(message.author.id)
        if message.author.bot:
            return

        if "早" in message.content or "午" in message.content or "晚" in message.content:
            if '早午晚' in message.content:
                await message.add_reaction('<:PaimonSeria:958341967698337854>')
                return
            check, msg = await self.flow_app.checkFlowAccount(user_id)
            if check == False:
                try:
                    await user.send(embed=msg)
                except:
                    pass
                return
            now = datetime.now()
            c: aiosqlite.Cursor = await self.bot.db.cursor()
            if "早" in message.content:
                start = datetime(year=now.year, month=now.month,
                                 day=now.day, hour=5, minute=0, second=0, microsecond=0)
                end = datetime(year=now.year, month=now.month, day=now.day,
                               hour=11, minute=59, second=0, microsecond=0)
                if start <= now <= end:
                    await c.execute('SELECT morning FROM flow_accounts WHERE user_id = ?', (user_id,))
                    morning = await c.fetchone()
                    if parser.parse(morning[0]).day != now.day:
                        await self.flow_app.transaction(
                            user_id, 1, time_state='morning')
                        await message.add_reaction('⛅')
            elif "午" in message.content:
                start = datetime(year=now.year, month=now.month, day=now.day,
                                 hour=12, minute=0, second=0, microsecond=0)
                end = datetime(year=now.year, month=now.month, day=now.day,
                               hour=17, minute=59, second=0, microsecond=0)
                if start <= now <= end:
                    await c.execute('SELECT noon FROM flow_accounts WHERE user_id = ?', (user_id,))
                    noon = await c.fetchone()
                    if parser.parse(noon[0]).day != now.day:
                        await self.flow_app.transaction(
                            user_id, 1, time_state='noon')
                        await message.add_reaction('☀️')
            elif "晚" in message.content:
                start = datetime(year=now.year, month=now.month, day=now.day,
                                 hour=18, minute=0, second=0, microsecond=0)
                end = datetime(year=now.year, month=now.month, day=now.day +
                               1, hour=4, minute=59, second=0, microsecond=0)
                if start <= now <= end:
                    await c.execute('SELECT night FROM flow_accounts WHERE user_id = ?', (user_id,))
                    night = await c.fetchone()
                    if parser.parse(night[0]).day != now.day:
                        await self.flow_app.transaction(
                            user_id, 1, time_state='night')
                        await message.add_reaction('🌙')

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        flow = await self.flow_app.get_user_flow(member.id)
        await self.flow_app.transaction(member.id, flow, is_removing_account=True)

    @app_commands.command(name='acc', description='查看flow帳號')
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的flow帳號')
    async def acc(self, i: Interaction, member: Member = None):
        member = member or i.user
        print(log(False, False, 'Acc', member.id))
        if i.channel.id == 960861105503232030:  # 委託台
            await i.response.send_message(embed=defaultEmbed('請不要在這裡使用/acc唷'), ephemeral=True)
            return
        now = datetime.now()
        check, msg = await self.flow_app.checkFlowAccount(member.id)
        if check == False:
            await i.response.send_message(embed=msg, ephemeral=True)
            return
        db: aiosqlite.Connection = self.bot.db
        c = await db.cursor()
        await c.execute('SELECT morning, noon, night FROM flow_accounts WHERE user_id = ?', (member.id,))
        result = await c.fetchone()
        flow = await self.flow_app.get_user_flow(member.id)
        time_state_str = ''
        time_coin_list = ['早安幣', '午安幣', '晚安幣']
        for index in range(0, 3):
            time_state_str += f'{time_coin_list[index]} {result[index]}\n'
        embed = defaultEmbed(
            f"flow帳號",
            f"flow幣: {flow}\n{time_state_str}")
        embed.set_author(name=member, icon_url=member.avatar)
        await i.response.send_message(embed=embed)

    @app_commands.command(name='give', description='給其他人flow幣')
    @app_commands.rename(member='某人', flow='要給予的flow幣數量')
    async def give(self, i: Interaction, member: Member, flow: int):
        print(log(False, False, 'Give',
              f'{i.user.id} give {flow} to {member.id}'))
        if member.id == i.user.id:
            await i.response.send_message(
                embed=errEmbed(
                    '不可以自己給自己flow幣',
                    '<:PaimonSeria:958341967698337854> 還想學土司跟ceye洗錢啊!'),
                ephemeral=True)
            return
        if flow < 0:
            await i.response.send_message(
                embed=errEmbed(
                    '不可以給負數flow幣',
                    '<:PaimonSeria:958341967698337854> 還想學土司跟ceye洗錢啊!'),
                ephemeral=True)
            return
        user_flow = await self.flow_app.get_user_flow(i.user.id)
        if user_flow < flow:
            embed = errEmbed(
                "❌ 交易失敗",
                "你的 flow幣數量不足已承擔這筆交易")
            await i.response.send_message(embed=embed, ephemeral=True)
            return
        await self.flow_app.transaction(i.user.id, -flow)
        await self.flow_app.transaction(member.id, flow)
        embed = defaultEmbed(
            "✅ 交易成功",
            f"{self.bot.get_user(i.user.id).mention} **- {flow}** flow幣\n"
            f"{self.bot.get_user(member.id).mention} **+ {flow}** flow幣")
        await i.response.send_message(content=f'{i.user.mention}{member.mention}', embed=embed)

    @app_commands.command(name='take', description='將某人的flow幣轉回銀行')
    @app_commands.rename(member='某人', flow='要拿取的flow幣數量', private='私人訊息')
    @app_commands.choices(private=[
        Choice(name='是', value=0),
        Choice(name='否', value=1)])
    @app_commands.checks.has_role('小雪團隊')
    async def take(self, i: Interaction, member: Member, flow: int, private: int):
        print(log(False, False, 'Take',
              f'{i.user.id} take {flow} from {member.id}'))
        check, msg = await self.flow_app.checkFlowAccount(member.id)
        if check == False:
            await i.response.send_message(embed=msg, ephemeral=True)
            return
        await self.flow_app.transaction(member.id, -flow)
        embed = defaultEmbed(
            "🌠 已成功施展「反」摩拉克斯的力量",
            f"{i.user.mention} 從 {self.bot.get_user(member.id).mention} 的帳戶裡拿走了**{flow}**枚flow幣"
        )
        ephemeral_toggler = True if private == 0 else False
        await i.response.send_message(embed=embed, ephemeral=ephemeral_toggler)

    @take.error
    async def err_handle(self, i: Interaction, e: app_commands.AppCommandError):
        if isinstance(e, app_commands.errors.MissingRole):
            await i.response.send_message('你不是小雪團隊的一員!', ephemeral=True)

    @app_commands.command(name='make', description='從銀行轉出flow幣給某人')
    @app_commands.rename(member='某人', flow='要給予的flow幣數量', private='私人訊息')
    @app_commands.choices(private=[
        Choice(name='是', value=0),
        Choice(name='否', value=1)])
    @app_commands.checks.has_role('小雪團隊')
    async def make(self, i: Interaction, member: Member, flow: int, private: int = 1):
        print(log(False, False, 'make',
              f'{i.user.id} make {flow} for {member.id}'))
        check, msg = await self.flow_app.checkFlowAccount(member.id)
        if check == False:
            await i.response.send_message(embed=msg, ephemeral=True)
            return
        await self.flow_app.transaction(member.id, int(flow))
        acceptor = self.bot.get_user(member.id)
        embed = defaultEmbed(
            "✨ 已成功施展摩拉克斯的力量",
            f"{i.user.mention} 給了 {acceptor.mention} {flow} 枚flow幣"
        )
        ephemeral_toggler = True if private == 0 else False
        await i.response.send_message(embed=embed, ephemeral=ephemeral_toggler)

    @make.error
    async def err_handle(self, i: Interaction, e: app_commands.AppCommandError):
        if isinstance(e, app_commands.errors.MissingRole):
            await i.response.send_message('你不是小雪團隊的一員!', ephemeral=True)

    @app_commands.command(name='total', description='查看目前群組帳號及銀行flow幣分配情況')
    async def total(self, i: Interaction):
        print(log(False, False, 'Total', f'{i.user.id}'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT SUM(flow) FROM flow_accounts')
        sum = await c.fetchone()
        bank = await self.flow_app.get_bank_flow()
        await c.execute('SELECT COUNT(*) FROM flow_accounts')
        account_count = await c.fetchone()
        embed = defaultEmbed(
            f'目前共{account_count[0]}個flow帳號',
            f'用戶 {sum[0]} +銀行 {bank} = {sum[0]+bank} 枚flow幣'
        )
        await i.response.send_message(embed=embed)

    @app_commands.command(name='flows', description='查看群組內所有flow帳號')
    async def flows(self, i: Interaction):
        flow_categories = {
            '小於 100 flow': [],
            '100~200 flow': [],
            '200~300 flow': [],
            '大於 300 flow': []
        }
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT user_id, flow FROM flow_accounts WHERE flow<100')
        result = await c.fetchall()
        for index, tuple in enumerate(result):
            flow_categories['小於 100 flow'].append(
                f'{i.client.get_user(tuple[0])}: {tuple[1]}')
        await c.execute('SELECT user_id, flow FROM flow_accounts WHERE flow BETWEEN 100 AND 200')
        result = await c.fetchall()
        for index, tuple in enumerate(result):
            flow_categories['100~200 flow'].append(
                f'{i.client.get_user(tuple[0])}: {tuple[1]}')
        await c.execute('SELECT user_id, flow FROM flow_accounts WHERE flow BETWEEN 201 AND 300')
        result = await c.fetchall()
        for index, tuple in enumerate(result):
            flow_categories['200~300 flow'].append(
                f'{i.client.get_user(tuple[0])}: {tuple[1]}')
        await c.execute('SELECT user_id, flow FROM flow_accounts WHERE flow>300')
        result = await c.fetchall()
        for index, tuple in enumerate(result):
            flow_categories['大於 300 flow'].append(
                f'{i.client.get_user(tuple[0])}: {tuple[1]}')
        embed_list = []
        for category, users in flow_categories.items():
            if len(users) == 0:
                continue
            value = ''
            for user in users:
                value += f'{user}\n'
            embed = defaultEmbed(f'{category} ({len(users)})', value)
            embed_list.append(embed)
        await GeneralPaginator(i, embed_list).start(embeded=True)

    shop = app_commands.Group(name="shop", description="flow商店")

    @shop.command(name='show', description='顯示商店')
    async def show(self, i: Interaction):
        print(log(False, False, 'shop show', i.user.id))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT name, flow, current, max FROM flow_shop')
        result = await c.fetchall()
        item_str = ''
        for index, tuple in enumerate(result):
            item_str += f'• {tuple[0]} - **{tuple[1]}** flow ({tuple[2]}/{tuple[3]})\n\n'
        embed = defaultEmbed("🛒 flow商店", item_str)
        await i.response.send_message(embed=embed)

    @shop.command(name='newitem', description='新增商品')
    @app_commands.rename(item='商品名稱', flow='價格', max='最大購買次數')
    @app_commands.checks.has_role('小雪團隊')
    async def newitem(self, i: Interaction, item: str, flow: int, max: int):
        print(log(False, False, 'shop newitem',
              f'{i.user.id}: (item={item}, flow={flow}, max={max})'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('INSERT INTO flow_shop(name) values(?)', (item,))
        await c.execute('UPDATE flow_shop SET flow = ?, current = 0, max = ? WHERE name = ?', (flow, max, item))
        await self.bot.db.commit()
        await i.response.send_message(f"商品**{item}**新增成功", ephemeral=True)

    @newitem.error
    async def err_handle(self, i: Interaction, e: app_commands.AppCommandError):
        if isinstance(e, app_commands.errors.MissingRole):
            await i.response.send_message('你不是小雪團隊的一員!', ephemeral=True)

    class ShopItemView(View):
        def __init__(self, item_names: List, action: str, db: aiosqlite.Connection):
            super().__init__(timeout=None)
            self.add_item(FlowCog.ShopItemSelect(item_names, action, db))

    class ShopItemSelect(Select):
        def __init__(self, item_names: List, action: str, db: aiosqlite.Connection):
            self.action = action
            self.db = db
            self.flow_app = FlowApp(self.db)
            options = []
            for item_name in item_names:
                options.append(SelectOption(label=item_name, value=item_name))
            super().__init__(placeholder=f'選擇商品', min_values=1, max_values=1, options=options)

        async def callback(self, i: Interaction) -> Any:
            c = await self.db.cursor()
            if self.action == 'remove':
                await c.execute('DELETE FROM flow_shop WHERE name = ?', (self.values[0],))
                await self.db.commit()
                await i.response.send_message(f'商品**{self.values[0]}**移除成功', ephemeral=True)
            elif self.action == 'buy':
                await c.execute('SELECT flow, current, max FROM flow_shop WHERE name= ?', (self.values[0],))
                result = await c.fetchone()
                flow: int = result[0]
                current: int = result[1]
                max: int = result[2]
                user_flow = await self.flow_app.get_user_flow(i.user.id)
                if user_flow < flow:
                    await i.response.send_message(embed=errEmbed("你的flow幣不足夠購買這項商品"), ephemeral=True)
                    return
                if current == max:
                    await i.response.send_message(embed=errEmbed("這個商品已經售罄了"), ephemeral=True)
                    return
                log_uuid = str(uuid.uuid4())
                await c.execute('INSERT INTO flow_shop_log (log_uuid) VALUES (?)', (log_uuid,))
                await c.execute('UPDATE flow_shop_log SET flow = ?, item = ?, buyer_id = ? WHERE log_uuid = ?', (int(flow), self.values[0], int(i.user.id), str(log_uuid)))
                await self.flow_app.transaction(i.user.id, -int(flow))
                await i.response.send_message(f"✨ {i.user.mention} 商品 **{self.values[0]}** 購買成功, 詳情請查看私訊")
                msg = await i.original_message()
                thread = await msg.create_thread(name=f'{i.user} • {self.values[0]} 購買討論串')
                await thread.add_user(i.user)
                lulurR = i.client.get_user(665092644883398671)
                await thread.add_user(lulurR)
                embed = defaultEmbed(
                    "📜 購買證明",
                    f"購買人: {i.user.mention}\n"
                    f"商品: {self.values[0]}\n"
                    f"收據UUID: {log_uuid}\n"
                    f"價格: {flow}")
                await thread.send(embed=embed)

    @shop.command(name='removeitem', description='刪除商品')
    @app_commands.checks.has_role('小雪團隊')
    async def removeitem(self, i: Interaction):
        print(log(False, False, 'shop removeitem', 'i.user.id'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT name FROM flow_shop')
        result = await c.fetchall()
        item_names = []
        for index, tuple in enumerate(result):
            item_names.append(tuple[0])
        view = FlowCog.ShopItemView(item_names, 'remove', self.bot.db)
        await i.response.send_message(view=view, ephemeral=True)

    @removeitem.error
    async def err_handle(self, i: Interaction, e: app_commands.AppCommandError):
        if isinstance(e, app_commands.errors.MissingRole):
            await i.response.send_message('你不是小雪團隊的一員!', ephemeral=True)

    @shop.command(name='buy', description='購買商品')
    async def buy(self, i: Interaction):
        print(log(False, False, 'shop buy', i.user.id))
        check, msg = await self.flow_app.checkFlowAccount(i.user.id)
        if check == False:
            await i.response.send_message(embed=msg, ephemeral=True)
            return
        item_names = []
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT name FROM flow_shop')
        result = await c.fetchall()
        for index, tuple in enumerate(result):
            item_names.append(tuple[0])
        view = FlowCog.ShopItemView(item_names, 'buy', self.bot.db)
        await i.response.send_message(view=view, ephemeral=True)

    def check_in_find_channel(self, channel_id: int):
        find_channel_id = 909595117952856084 if debug_toggle else 960861105503232030
        if channel_id != find_channel_id:
            channel = self.bot.get_channel(find_channel_id)
            return False, f"請在{channel.mention}裡使用此指令"
        else:
            return True, None

    async def check_flow(self, user_id: int, flow: int):
        user_flow = await self.flow_app.get_user_flow(user_id)
        if int(flow) < 0:
            result = errEmbed("發布失敗, 請輸入大於 1 的flow幣", "")
            return False, result
        elif user_flow < int(flow):
            result = errEmbed("發布失敗, 請勿輸入大於自己擁有數量的flow幣", "")
            return False, result
        else:
            return True, None

    class AcceptView(discord.ui.View):
        def __init__(self, author: Member, db: aiosqlite.Connection):
            self.author = author
            self.db = db
            super().__init__(timeout=None)

        async def interaction_check(self, i: Interaction) -> bool:
            return i.user.id != self.author.id

        @discord.ui.button(label='接受委託', style=discord.ButtonStyle.green, custom_id='accept_commision_button')
        async def confirm(self, i: Interaction, button: discord.ui.Button):
            button.disabled = True
            await i.response.edit_message(view=self)
            msg = i.message
            c: aiosqlite.Cursor = await self.db.cursor()
            await c.execute('SELECT * FROM find WHERE msg_id = ?', (msg.id,))
            result = await c.fetchone()
            flow = result[1]
            title = result[2]
            type = result[3]
            author_id = result[4]
            print(log(True, False, 'Accept',
                  f"(author = {author_id}, confirmer = {i.user.id})"))
            author = i.client.get_user(author_id)
            confirmer = i.client.get_user(i.user.id)
            thread = await msg.create_thread(name=f"{author.name} • {title}")
            await thread.add_user(author)
            await thread.add_user(confirmer)
            action_str = ['委託', '素材委託', '委託', '幫助']
            for index in range(1, 5):
                if type == index:
                    await i.followup.send(f"✅ {confirmer.mention} 已接受 {author.mention} 的 **{title}** {action_str[index-1]}")
            if type == 4:
                embedDM = defaultEmbed(
                    f"結算單",
                    f"當{confirmer.mention}完成幫忙的內容時, 請按OK來結算flow幣\n"
                    f"按下後, 你的flow幣將會 **-{flow}**\n"
                    f"對方則會 **+{flow}**")
            else:
                embedDM = defaultEmbed(
                    f"結算單",
                    f"當{confirmer.mention}完成委託的內容時, 請按OK來結算flow幣\n"
                    f"按下後, 你的flow幣將會 **-{flow}**\n"
                    f"對方則會 **+{flow}**")
            embedDM.set_author(name=author, icon_url=author.avatar)
            view = FlowCog.ConfirmView(author, self.db)
            confirm_message = await thread.send(embed=embedDM, view=view)
            await c.execute('UPDATE find SET msg_id = ?, confirmer_id = ?', (confirm_message.id, i.user.id))
            await self.db.commit()

    class ConfirmView(discord.ui.View):
        def __init__(self, author: Member, db: aiosqlite.Connection):
            self.author = author
            self.db = db
            self.flow_app = FlowApp(self.db)
            super().__init__(timeout=None)

        async def interaction_check(self, i: Interaction) -> bool:
            return i.user.id == self.author.id

        @discord.ui.button(label='OK', style=discord.ButtonStyle.blurple, custom_id='ok_confirm_button')
        async def ok_confirm(self, i: Interaction, button: Button):
            print(log(False, False, 'OK Confirm', f'confirmer = {i.user.id}'))
            c: aiosqlite.Cursor = await self.db.cursor()
            await c.execute('SELECT * FROM find WHERE msg_id = ?', (i.message.id,))
            result = await c.fetchone()
            flow = result[1]
            title = result[2]
            type = result[3]
            author_id = result[4]
            confirmer_id = result[5]
            str = ''
            author = i.client.get_user(author_id)
            confirmer = i.client.get_user(confirmer_id)
            await c.execute('SELECT find_free_trial FROM flow_accounts WHERE user_id = ?', (author_id,))
            result = await c.fetchone()
            author_free_trial = result[0]
            await c.execute('SELECT find_free_trial FROM flow_accounts WHERE user_id = ?', (confirmer_id,))
            result = await c.fetchone()
            confirmer_free_trial = result[0]
            if type == 4:
                if confirmer_free_trial < 10 and flow >= 10:
                    new_flow = flow-10
                    await c.execute('UPDATE flow_accounts SET find_free_trial = ? WHERE user_id = ?', (confirmer_free_trial+1, confirmer_id))
                    str = f'({confirmer.mention}受到 10 flow幣贊助)\n'
                    f'已使用 {confirmer_free_trial+1}/10 次贊助機會'
                await self.flow_app.transaction(author_id, flow)
                await self.flow_app.transaction(confirmer_id, -int(new_flow))
                embed = defaultEmbed(
                    "🆗 結算成功",
                    f"幫忙名稱: {title}\n"
                    f"幫助人: {author.mention} **+{flow}** flow幣\n"
                    f"被幫助人: {confirmer.mention} **-{new_flow}** flow幣\n{str}")
            else:
                if author_free_trial < 10 and flow >= 10:
                    new_flow = flow-10
                    await c.execute('UPDATE flow_accounts SET find_free_trial = ? WHERE user_id = ?', (author_free_trial+1, author_id))
                    str = f'({author.mention}受到 10 flow幣贊助)\n'
                    f'已使用 {author_free_trial+1}/10 次贊助機會'
                await self.flow_app.transaction(author_id, -int(new_flow))
                await self.flow_app.transaction(confirmer_id, flow)
                embed = defaultEmbed(
                    "🆗 結算成功",
                    f"委託名稱: {title}\n"
                    f"委託人: {author.mention} **-{new_flow}** flow幣\n"
                    f"接收人: {confirmer.mention} **+{flow}** flow幣\n{str}")
            await i.response.send_message(embed=embed)
            t = i.guild.get_thread(i.channel.id)
            await t.edit(archived=True)
            await c.execute('DELETE FROM find WHERE msg_id = ?', (i.message.id,))
            await self.db.commit()

    @app_commands.command(name='find', description='發布委託')
    @app_commands.rename(type='委託類型', title='幫助名稱', flow='flow幣數量', tag='tag人開關')
    @app_commands.describe(title='需要什麼幫助?', flow='這個幫助值多少flow幣?', tag='是否要tag委託通知?')
    @app_commands.choices(type=[
        Choice(name='1類委託 其他玩家進入你的世界(例如: 陪玩, 打素材等)', value=1),
        Choice(name='2類委託 你進入其他玩家的世界(例如: 拿特產)', value=2),
        Choice(name='3類委託 其他委託(例如: 打apex, valorant)', value=3),
        Choice(name='4類委託 可以幫助別人(讓拿素材, 可幫打刀鐔等)', value=4)],
        tag=[Choice(name='不tag', value=0),
             Choice(name='tag', value=1)])
    async def find(self, i: Interaction, type: int, title: str, flow: int, tag: int = 1):
        print(log(False, False, 'Find',
              f'{i.user.id}: (type={type}, title={title}, flow={flow})'))
        check, msg = self.check_in_find_channel(i.channel.id)
        if check == False:
            await i.response.send_message(msg, ephemeral=True)
            return
        check, msg = await self.flow_app.checkFlowAccount(i.user.id)
        if check == False:
            await i.response.send_message(embed=msg, ephemeral=True)
            return
        role_name = f'請使用`/role`來選擇世界等級身份組'
        if not debug_toggle:
            WLroles = []
            for index in range(1, 9):
                WLroles.append(discord.utils.get(
                    i.user.guild.roles, name=f"W{str(index)}"))
            for r in WLroles:
                if r in i.user.roles:
                    role_name = r.name
                    break
        check, msg = await self.check_flow(i.user.id, flow)
        if check == False:
            await i.response.send_message(embed=msg)
            return
        role_str = f'>= {role_name}' if type ==1 else f'<= {role_name}'
        if type == 1:
            embed = defaultEmbed(
                f'請求幫助: {title}',
                f'發布者: {i.user.mention}\n'
                f'flow幣: {flow}\n'
                f'世界等級: {role_str}\n'
            )
        elif type == 2:
            embed = defaultEmbed(
                f'請求幫助: {title}',
                f'發布者: {i.user.mention}\n'
                f'flow幣: {flow}\n'
                f'世界等級: {role_str}\n'
            )
        elif type == 3:
            embed = defaultEmbed(
                f'請求幫助: {title}',
                f'發布者: {i.user.mention}\n'
                f'flow幣: {flow}'
            )
        elif type == 4:
            embed = defaultEmbed(
                f'可以幫忙: {title}',
                f'發布者: {i.user.mention}\n'
                f'flow幣: {flow}\n'
                f'發布者世界等級: {role_name}\n'
            )
        if tag == 1:
            g = self.bot.get_guild(916838066117824553)  # 緣神有你
            role = g.get_role(965141973700857876)  # 委託通知
            await i.channel.send(role.mention)
        view = self.AcceptView(i.user, self.bot.db)
        await i.response.send_message(embed=embed, view=view)
        msg = await i.original_message()
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('INSERT INTO find(msg_id, flow, title, type, author_id) VALUES (?, ?, ?, ?, ?)', (msg.id, flow, title, type, i.user.id))
        await self.bot.db.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FlowCog(bot))
