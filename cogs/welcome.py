import random
import aiosqlite
from discord import ButtonStyle, Guild, Interaction, Member, app_commands
from discord.ext import commands
from discord.ui import Button, View, button
from utility.FlowApp import FlowApp
from utility.utils import defaultEmbed
from utility.TutorialPaginator import TutorialPaginator


class WelcomeCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.flow_app = FlowApp(self.bot.db)

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT * FROM guild_members WHERE user_id = ?', (member.id,))
        result = await c.fetchone()
        if result is None:
            await c.execute('INSERT INTO guild_members (user_id) VALUES (?)', (member.id,))
            self.flow_app.register(member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        flow = await self.flow_app.get_user_flow(member.id)
        await self.flow_app.transaction(member.id, flow, is_removing_account=True)

    class Welcome(View):
        def __init__(self, member: Member):
            self.member = member
            super().__init__(timeout=None)

        @button(label='歡迎~', style=ButtonStyle.blurple, custom_id='welcome_button')
        async def welcome(self, i: Interaction, button: Button):
            image_urls = ['https://media.discordapp.net/attachments/936772657536446535/978537906538954782/mhQ174-icc4ZdT1kSdw-dw.gif', 'https://images-ext-1.discordapp.net/external/Le6fh1tAi0HoIJ645bmMdznShROcixc1_cMVhdwSOQ8/, https://media.discordapp.net/attachments/630553822036623370/946061268828192829/don_genshin220223.gif', 'https://media.discordapp.net/attachments/813430632347598882/821418716243427419/d6bf3d80f1151c55.gif', 'https://images-ext-2.discordapp.net/external/ZT2POprq370cRqLSihczTLR04h7yWDJ6sYDS0SlwbL0/https/media.discordapp.net/attachments/630553822036623370/811578439852228618/kq_genshin210217.gif', 'https://images-ext-1.discordapp.net/external/5WaTn6d2bg7xDlfVsKI22nbHyfr0j-t58VzkampNkXM/https/media.discordapp.net/attachments/630553822036623370/810819929187155968/kq.gif',
                          'https://images-ext-2.discordapp.net/external/AjGrIlK21bVWi-Nl_L6gdfbkvwo_ijZKE6-F3mNNIJo/, https://media.discordapp.net/attachments/630553822036623370/865978275125264414/ayk_genshin210717.gif', 'https://images-ext-1.discordapp.net/external/r0KCbNATVYUb3QzgliOmVKzzP2FxkBb3aDCHFJkz7x0/, https://media.discordapp.net/attachments/630553822036623370/890615080381730836/kkm_genshin210923.gif', 'https://images-ext-2.discordapp.net/external/7rQjNK6dkCjXsF7n70Kn4qorxGyiBiX9dlzQvP2R-9c/https/media.discordapp.net/attachments/630553822036623370/840964488362590208/qq_genshin210509.gif', 'https://images-ext-2.discordapp.net/external/6OXz15XV0RNCIkbFCjXCYUPx7h1zNcZ1inqNYo0vkiM/https/media.discordapp.net/attachments/630553822036623370/920326390329516122/rid_genshin211214.gif', 'https://images-ext-2.discordapp.net/external/NqQ8IkDIOfxEp_FoobMySLzlW2JDAa1lK8IxQOVvxng/https/media.discordapp.net/attachments/630553822036623370/866703863276240926/rdsg_genshin210719.gif']
            image_url = random.choice(image_urls)
            embed = defaultEmbed(f'{self.member.name} 歡迎歡迎~','<:penguin_hug:978250194779000892>')
            embed.set_thumbnail(url=image_url)
            embed.set_author(name=i.user.name, icon_url=i.user.avatar)
            await i.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        g: Guild = self.bot.get_guild(916838066117824553)
        r = g.get_role(978532779098796042)
        if r not in before.roles and r in after.roles:
            c = self.bot.get_channel(916951131022843964)
            view = WelcomeCog.Welcome(after)
            welcome_strs = ['祝你保底不歪十連雙黃', '祝你10連全武器 <:ehe:956180671620055050> <:ehe:956180671620055050>',
                            '希望你喜歡並享受這裡充滿歡笑和||變態||的氣氛', '我們群中都是喜歡玩原神的||大課長||玩家!', '歡迎你成為我們的一份子||(扣上鐵鏈)||']
            welcome_str = random.choice(welcome_strs)
            embed = defaultEmbed(
                f'歡迎 {after.name} !', f'歡迎來到緣神有你(๑•̀ω•́)ノ\n {welcome_str}')
            embed.set_thumbnail(url=after.avatar)
            await c.send(content=after.mention, embed=embed, view=view)

    class AcceptRules(View):
        def __init__(self):
            super().__init__(timeout=None)

        @button(label='同意以上規則並開始入群導引', style=ButtonStyle.green, custom_id='accept_rule_button')
        async def accept_rules(self, i: Interaction, button: Button):
            embed = defaultEmbed(
                '入群導引',
                '為了讓你進入群組後能更快速適應,\n'
                '申鶴將會快速的帶領你了解群內的主要系統\n'
                '這可以幫助你獲得免費的原神月卡及其他好物\n'
                '請有耐心的做完唷~ <:penguin_hug:978250194779000892>'
            )
            view = WelcomeCog.StartTutorial()
            await i.response.send_message(embed=embed, view=view, ephemeral=True)

    class StartTutorial(View):
        def __init__(self):
            super().__init__(timeout=None)

        @button(label='開始!', style=ButtonStyle.blurple, custom_id='start_tutorial_button')
        async def start_tutorial(self, i: Interaction, button: Button):
            embeds = []
            embed = defaultEmbed(
                '原神系統',
                '先從輸入你的原神UID開始吧!\n'
                '請輸入`/setuid`指令來設置UID\n'
                '如果跳出錯誤訊息, 請按照指示操作'
            )
            embeds.append(embed)
            factory = i.client.get_channel(957268464928718918)
            embed = defaultEmbed(
                '原神系統',
                '申鶴有許多原神相關的方便功能\n'
                '如樹脂查詢, 角色查詢, 自動簽到, 樹脂提醒, 祈願分析, 深淵數據等...\n'
                f'有興趣的話, 可以至 {factory.mention} 使用`/cookie`設置帳號'
            )
            embeds.append(embed)
            embed = defaultEmbed(
                'flow幣系統',
                '這是群內專屬的經濟系統\n'
                '在你入群的時候, 系統已經幫你創建一個帳號\n'
                '並贈送了20 flow幣給你\n'
                '輸入`/acc`來看看你的 **flow帳號** 吧!'
            )
            embeds.append(embed)
            gv = i.client.get_channel(965517075508498452)
            role = i.client.get_channel(962311051683192842)
            embed = defaultEmbed(
                '抽獎系統',
                f'抽獎都會在 {gv.mention} 進行\n'
                '抽獎需要支付flow幣來參與\n'
                f'可以到 {role.mention} 領取 **抽獎通知** 身份組'
            )
            c = i.client.get_channel(960861105503232030)
            embeds.append(embed)
            embed = defaultEmbed(
                '委託系統',
                f'萌新:歡迎到 {c.mention} 使用`/find`指令來發布委託\n'
                f'大佬:可以到 {role.mention} 領取 **委託通知** 身份組\n\n'
                '可以免費發布委託, 也可以花費 **flow幣 **發布\n'
                '接取委託有機會獲得 **flow幣** (取決於發布人)'
            )
            embeds.append(embed)
            flow_c = i.client.get_channel(966621141949120532)
            embed = defaultEmbed(
                'flow幣活動',
                '每週都會有不同的活動來取得flow幣\n'
                '包括討伐挑戰, 拍照等等...盡量符合不同玩家的風格\n'
                f'有興趣請往 {flow_c.mention}'
            )
            embeds.append(embed)
            embed = defaultEmbed(
                '祈願系統',
                '我們在discord中複製了原神的祈願玩法\n'
                '可以使用`/roll`指令來開啟祈願界面(不要直接在這裡用哦)\n'
                '有機率抽中不同物品, 取決於當期獎品'
            )
            embeds.append(embed)
            embed = defaultEmbed(
                '商店系統',
                '賺到的 **flow幣** 可以在商店進行消費\n'
                '輸入`/shop show`來看看吧\n'
                '當你賺到足夠的錢後, 可以用`/shop buy`來購買商品'
            )
            embeds.append(embed)
            embed = defaultEmbed(
                '還有更多...',
                '以上只是申鶴的一小部份而已!\n'
                '想要查看所有的指令請打`/help`(不要直接在這裡用哦)\n'
                f'有問題歡迎至 {factory.mention} 詢問我(小雪)'
            )
            embeds.append(embed)
            embed = defaultEmbed(
                '祝你好運!',
                '以上就是入群導引\n'
                '歡迎加入「緣神有你」!\n'
                '在這裡好好享受歡樂的時光吧!'
            )
            embeds.append(embed)
            await TutorialPaginator(i, embeds).start(embeded=True)

    @app_commands.command(name='welcome', description='送出welcome message')
    async def welcome(self, i: Interaction):
        content = '旅行者們，歡迎來到「緣神有你」。\n在這裡你能收到提瓦特的二手消息, 還能找到志同道合的旅行者結伴同行。\n準備好踏上旅途了嗎? 出發前請先閱讀下方的「旅行者須知」。\n'
        rules = defaultEmbed(
            '🔖旅行者須知',
            '⚠️以下違規情形發生，將直接刪除貼文並禁言\n\n'
            '1. 張貼侵權事物的網址或載點\n'
            '2. 惡意引戰 / 惡意帶風向 / 仇恨言論或霸凌 / 煽動言論\n'
            '3. 交換 / 租借 / 買賣遊戲帳號、外掛\n'
            '4. 在色色台以外發表色情訊息 / 大尺度圖片 / 露點或者其他暴露圖 / \n使人感到不適的圖片或表情 / 以上相關連結\n'
            '5. 發送大量無意義言論洗版\n'
            '6. 討論政治相關內容\n'
            '7. 以暱稱惡搞或假冒管理員以及官方帳號 / 使用不雅的暱稱或簽名\n'
            '8. 推銷或發布垃圾訊息\n'
            '9. 私訊騷擾其他旅行者\n\n'
            '以上守則會隨著大家違規的創意和台主們的心情不定時更新, 感謝遵守規則的各位~\n'
        )
        view = WelcomeCog.AcceptRules()
        await i.response.send_message(content=content, embed=rules, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
