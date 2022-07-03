import re
from datetime import datetime

import aiosqlite
import genshin
from discord import Embed
from discord.ext import commands
from utility.utils import (defaultEmbed, errEmbed, getAreaEmoji, getCharacter,
                           getClient, getWeapon, getWeekdayName, log,
                           trimCookie)


class GenshinApp:
    def __init__(self, db: aiosqlite.Connection, bot: commands.Bot) -> None:
        self.db = db
        self.bot = bot

    async def setCookie(self, user_id: int, cookie: str):
        log(False, False, 'setCookie', f'{user_id} (cookie = {cookie})')
        user = self.bot.get_user(user_id)
        user_id = int(user_id)
        cookie = trimCookie(cookie)
        if cookie == None:
            result = errEmbed(
                message='輸入 `/cookie` 來查看設定方式').set_author(name='無效的 cookie', icon_url=user.avatar)
            return result, False
        client = genshin.Client(lang='zh-tw')
        client.set_cookies(cookie)
        accounts = await client.get_game_accounts()
        if len(accounts) == 0:
            result = errEmbed(message='已取消設定 cookie').set_author(
                name='帳號內沒有任何角色')
            return result, False
        c: aiosqlite.Cursor = await self.db.cursor()
        await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (user_id,))
        uid = await c.fetchone()
        if uid is None:
            result = errEmbed('請至 <#978871680019628032> 註冊 UID').set_author(
                name='找不到 UID', icon_url=user.avatar)
            return result, False
        uid = uid[0]
        uid_found = False
        for account in accounts:
            if account.uid == uid:
                uid_found = True
                break
        if not uid_found:
            result = errEmbed(message='你在 <#978871680019628032> 輸入的 UID 與你在遊戲內的 UID 不符\n'
                              '請在確認過後至 <#978871680019628032> 重新輸入 UID'
                              ).set_author(name='UID 錯誤', icon_url=user.avatar)
            return result, False
        ltoken = re.search(
            '[0-9A-Za-z]{20,}', cookie).group()
        ltuid_str = re.search('ltuid=[0-9]{3,}', cookie).group()
        ltuid = int(
            re.search(r'\d+', ltuid_str).group())
        cookie_token = (
            re.search('cookie_token=[0-9A-Za-z]{20,}', cookie).group())[13:]
        c: aiosqlite.Cursor = await self.db.cursor()
        await c.execute('UPDATE genshin_accounts SET ltuid = ?, ltoken = ?, cookie_token = ? WHERE user_id = ?', (ltuid, ltoken, cookie_token, user_id))
        log(False, False, 'setCookie', f'{user_id} set cookie success')
        result = defaultEmbed().set_author(name='cookie 設定完成', icon_url=user.avatar)
        await self.db.commit()
        return result, True

    async def setUID(self, user_id: int, uid: int):
        log(False, False, 'setUID', f'{user_id}: (uid = {uid})')
        user = self.bot.get_user(user_id)
        c: aiosqlite.Cursor = await self.db.cursor()
        if len(str(uid)) != 9:
            return errEmbed().set_author(name='請輸入長度為9的UID!', icon_url=user.avatar), False
        if uid//100000000 != 9:
            result = errEmbed(message='非常抱歉, 「緣神有你」是一個台澳港服為主的群組\n'
                              '為保群友的遊戲質量, 我們無法接受你的入群申請\n'
                              '我們真心認為其他群組對你來說可能是個更好的去處 🙏').set_author(name='你似乎不是台港澳服玩家!', icon_url=user.avatar)
            return result, False
        await c.execute('SELECT user_id FROM genshin_accounts WHERE uid = ?', (uid,))
        result = await c.fetchone()
        if result is not None:
            return errEmbed(message=f'你輸入的 UID 已經在資料庫裡了\n註冊人為: {(self.bot.get_user(result[0])).mention}').set_author(name='UID 重複', icon_url=user.avatar), False
        client = getClient()
        try:
            genshinUser = await client.get_partial_genshin_user(uid)
        except genshin.errors.AccountNotFound:
            return errEmbed(message='請檢查有無輸入錯誤').set_author(name='無效的 UID', icon_url=user.avatar), False
        await c.execute('SELECT * FROM genshin_accounts WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        if result is None:
            await c.execute('INSERT INTO genshin_accounts (user_id, uid) VALUES (?, ?)', (user_id, uid))
        else:
            await c.execute('UPDATE genshin_accounts SET uid = ? WHERE user_id = ?', (uid, user_id))
        await self.db.commit()
        return defaultEmbed(message=uid).set_author(name='設置成功', icon_url=user.avatar), True

    async def claimDailyReward(self, user_id: int):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        if only_uid:
            return errEmbed(message='使用 `/cookie` 指令來註冊').set_author(name='請註冊 cookie', icon_url=user.avatar), False
        try:
            reward = await client.claim_daily_reward()
        except genshin.errors.AlreadyClaimed:
            return errEmbed().set_author(name='你已經領過今天的獎勵了!', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            return defaultEmbed(message=f'獲得 {reward.amount}x {reward.name}').set_author(name='簽到成功', icon_url=user.avatar), True

    async def getRealTimeNotes(self, user_id: int, check_resin_excess=False):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        if only_uid:
            return errEmbed(message='使用 `/cookie` 指令來註冊').set_author(name='請註冊 cookie', icon_url=user.avatar), False
        try:
            notes = await client.get_notes(uid)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            if check_resin_excess:
                return notes.current_resin, True
            else:
                return self.parseResinEmbed(notes).set_author(name='即時便籤', icon_url=user.avatar), True

    def parseResinEmbed(self, notes) -> Embed:
        if notes.current_resin == notes.max_resin:
            resin_recover_time = '已滿'
        else:
            day_msg = '今天' if notes.resin_recovery_time.day == datetime.now().day else '明天'
            resin_recover_time = f'{day_msg} {notes.resin_recovery_time.strftime("%H:%M")}'

        if notes.current_realm_currency == notes.max_realm_currency:
            realm_recover_time = '已滿'
        else:
            weekday_msg = getWeekdayName(
                notes.realm_currency_recovery_time.weekday())
            realm_recover_time = f'{weekday_msg} {notes.realm_currency_recovery_time.strftime("%H:%M")}'
        if notes.transformer_recovery_time != None:
            t = notes.remaining_transformer_recovery_time
            if t.days > 0:
                recover_time = f'剩餘 {t.days} 天'
            elif t.hours > 0:
                recover_time = f'剩餘 {t.hours} 小時'
            elif t.minutes > 0:
                recover_time = f'剩餘 {t.minutes} 分'
            elif t.seconds > 0:
                recover_time = f'剩餘 {t.seconds} 秒'
            else:
                recover_time = '可使用'
        else:
            recover_time = '質變儀不存在'
        result = defaultEmbed(
            f"",
            f"<:daily:956383830070140938> 已完成的每日數量: {notes.completed_commissions}/{notes.max_commissions}\n"
            f"<:transformer:966156330089971732> 質變儀剩餘時間: {recover_time}"
        )
        result.add_field(
            name='<:resin:956377956115157022> 樹脂',
            value=f" 目前樹脂: {notes.current_resin}/{notes.max_resin}\n"
            f"樹脂回滿時間: {resin_recover_time}\n"
            f'週本樹脂減半: 剩餘 {notes.remaining_resin_discounts}/3 次',
            inline=False
        )
        result.add_field(
            name='<:realm:956384011750613112> 塵歌壺',
            value=f" 目前洞天寶錢數量: {notes.current_realm_currency}/{notes.max_realm_currency}\n"
            f'寶錢全部恢復時間: {realm_recover_time}',
            inline=False
        )
        exped_finished = 0
        exped_msg = ''
        if not notes.expeditions:
            exped_msg = '沒有探索派遣'
            total_exped = 0
        for expedition in notes.expeditions:
            total_exped = len(notes.expeditions)
            exped_msg += f'• {getCharacter(expedition.character.id)["name"]}'
            if expedition.finished:
                exped_finished += 1
                exped_msg += ': 已完成\n'
            else:
                day_msg = '今天' if expedition.completion_time.day == datetime.now().day else '明天'
                exped_msg += f' 完成時間: {day_msg} {expedition.completion_time.strftime("%H:%M")}\n'
        result.add_field(
            name=f'<:pin:984677478490570762> 探索派遣 ({exped_finished}/{total_exped})',
            value=exped_msg,
            inline=False
        )
        return result

    async def getUserStats(self, user_id: int):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        try:
            genshinUser = await client.get_partial_genshin_user(uid)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            characters = await client.get_calculator_characters()
            result = defaultEmbed()
            result.add_field(
                name='綜合',
                value=f"📅 活躍天數: {genshinUser.stats.days_active}\n"
                f"<:expedition:956385168757780631> 角色數量: {genshinUser.stats.characters}/{len(characters)}\n"
                f"📜 成就數量:{genshinUser.stats.achievements}/639\n"
                f"🌙 深淵已達: {genshinUser.stats.spiral_abyss}層",
                inline=False)
            result.add_field(
                name='神瞳',
                value=f"<:anemo:956719995906322472> 風神瞳: {genshinUser.stats.anemoculi}/66\n"
                f"<:geo:956719995440730143> 岩神瞳: {genshinUser.stats.geoculi}/131\n"
                f"<:electro:956719996262821928> 雷神瞳: {genshinUser.stats.electroculi}/181", inline=False)
            result.add_field(
                name='寶箱',
                value=f"一般寶箱: {genshinUser.stats.common_chests}\n"
                f"稀有寶箱: {genshinUser.stats.exquisite_chests}\n"
                f"珍貴寶箱: {genshinUser.stats.luxurious_chests}",
                inline=False)
        return result.set_author(name='原神數據', icon_url=user.avatar), True

    async def getArea(self, user_id: int):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        try:
            genshinUser = await client.get_partial_genshin_user(uid)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            explorations = genshinUser.explorations
            explore_str = ""
            for exploration in reversed(explorations):
                level_str = '' if exploration.name == '淵下宮' or exploration.name == '層岩巨淵' else f'- Lvl. {exploration.level}'
                emoji_name = getAreaEmoji(exploration.name)
                explore_str += f"{emoji_name} {exploration.name} {exploration.explored}% {level_str}\n"
            result = defaultEmbed(message=explore_str)
        return result.set_author(name='區域探索度', icon_url=user.avatar), True

    async def getDiary(self, user_id: int, month: int):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        try:
            diary = await client.get_diary(month=month)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            d = diary.data
            result = defaultEmbed(
                f'{month}月',
                f'原石收入比上個月{"增加" if d.primogems_rate > 0 else "減少"}了{abs(d.primogems_rate)}%\n'
                f'摩拉收入比上個月{"增加" if d.mora_rate > 0 else "減少"}了{abs(d.mora_rate)}%'
            )
            result.add_field(
                name='本月共獲得',
                value=f'<:primo:958555698596290570> {d.current_primogems} ({int(d.current_primogems/160)} <:pink_ball:984652245851316254>) • 上個月: {d.last_primogems} ({int(d.last_primogems/160)} <:pink_ball:984652245851316254>)\n'
                f'<:mora:958577933650362468> {d.current_mora} • 上個月: {d.last_mora}',
                inline=False
            )
            msg = ''
            for cat in d.categories:
                msg += f'{cat.name}: {cat.percentage}%\n'
            result.add_field(name=f'收入分類', value=msg, inline=False)
        return result.set_author(name='旅行者日記', icon_url=user.avatar), True

    async def getDiaryLog(self, user_id: int):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        try:
            diary = await client.get_diary()
        except genshin.errors.DataNotPublic as e:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            primoLog = ''
            result = []
            async for action in client.diary_log(limit=25):
                primoLog = primoLog + \
                    f"{action.action} - {action.amount} 原石"+"\n"
            embed = defaultEmbed(message=f"{primoLog}")
            embed.set_author(name='原石獲取紀錄', icon_url=user.avatar)
            result.append(embed)
            moraLog = ''
            async for action in client.diary_log(limit=25, type=genshin.models.DiaryType.MORA):
                moraLog = moraLog+f"{action.action} - {action.amount} 摩拉"+"\n"
            embed = defaultEmbed(message=f"{moraLog}")
            embed.set_author(name='摩拉獲取紀錄', icon_url=user.avatar)
            result.append(embed)
        return result, True

    async def getAbyss(self, user_id: int, previous: bool, overview: bool):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        if only_uid:
            return errEmbed(message='使用 `/cookie` 指令來註冊').set_author(name='請註冊 cookie', icon_url=user.avatar),
        try:
            abyss = await client.get_spiral_abyss(uid, previous=previous)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            rank = abyss.ranks
            if len(rank.most_kills) == 0:
                result = errEmbed(message='請輸入 `/stats` 來刷新資料\n'
                                  '(深淵資料需最多1小時來接收)').set_author(name='找不到深淵資料', icon_url=user.avatar), False
                return result
            result = defaultEmbed(
                f"第{abyss.season}期深淵",
                f"獲勝場次: {abyss.total_wins}/{abyss.total_battles}\n"
                f"達到{abyss.max_floor}層\n"
                f"共{abyss.total_stars} ✦"
            )
            result.add_field(
                name="戰績",
                value=f"單次最高傷害 • {getCharacter(rank.strongest_strike[0].id)['name']} • {rank.strongest_strike[0].value}\n"
                f"擊殺王 • {getCharacter(rank.most_kills[0].id)['name']} • {rank.most_kills[0].value}次擊殺\n"
                f"最常使用角色 • {getCharacter(rank.most_played[0].id)['name']} • {rank.most_played[0].value}次\n"
                f"最多Q使用角色 • {getCharacter(rank.most_bursts_used[0].id)['name']} • {rank.most_bursts_used[0].value}次\n"
                f"最多E使用角色 • {getCharacter(rank.most_skills_used[0].id)['name']} • {rank.most_skills_used[0].value}次"
            )
            result.set_author(name='深淵總覽', icon_url=user.avatar)
            if overview:
                return [result], True
            result = []
            for floor in abyss.floors:
                embed = defaultEmbed().set_author(name=f"第{floor.floor}層 (共{floor.stars} ✦)")
                for chamber in floor.chambers:
                    name = f'第{chamber.chamber}間 {chamber.stars} ✦'
                    chara_list = [[], []]
                    for i, battle in enumerate(chamber.battles):
                        for chara in battle.characters:
                            chara_list[i].append(
                                getCharacter(chara.id)['name'])
                    topStr = ''
                    bottomStr = ''
                    for top_char in chara_list[0]:
                        topStr += f"• {top_char} "
                    for bottom_char in chara_list[1]:
                        bottomStr += f"• {bottom_char} "
                    embed.add_field(
                        name=name,
                        value=f"[上半] {topStr}\n\n"
                        f"[下半] {bottomStr}",
                        inline=False
                    )
                result.append(embed)
        return result, True

    async def getBuild(self, element_dict: dict, chara_name: str):
        charas = dict(element_dict)
        result = []
        name = chara_name
        count = 1
        has_thoughts = False
        for build in charas[chara_name]['builds']:
            statStr = ''
            for stat, value in build['stats'].items():
                statStr += f'{stat} ➜ {value}\n'
            embed = defaultEmbed(
                f'{name} - 配置{count}',
                f"武器 • {getWeapon(name=build['weapon'])['emoji']} {build['weapon']}\n"
                f"聖遺物 • {build['artifacts']}\n"
                f"主詞條 • {build['main_stats']}\n"
                f"天賦 • {build['talents']}\n"
                f"{build['move']} • {build['dmg']}\n\n"
            )
            embed.add_field(
                name=f"屬性面版",
                value=statStr
            )
            count += 1
            embed.set_thumbnail(
                url=getCharacter(name=name)["icon"])
            embed.set_footer(
                text='[來源](https://bbs.nga.cn/read.php?tid=25843014)')
            result.append([embed, build['weapon'], build['artifacts']])
        if 'thoughts' in charas[chara_name]:
            has_thoughts = True
            count = 1
            embed = defaultEmbed(f'聖遺物思路')
            for thought in charas[chara_name]['thoughts']:
                embed.add_field(name=f'思路{count}',
                                value=thought, inline=False)
                count += 1
            embed.set_thumbnail(
                url=getCharacter(name=name)["icon"])
            result.append([embed, '', ''])
        return result, has_thoughts

    async def setResinNotification(self, user_id: int, resin_notification_toggle: int, resin_threshold: int, max_notif: int):
        c: aiosqlite.Cursor = await self.db.cursor()
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        if only_uid:
            return errEmbed(message='使用 `/cookie` 指令來註冊').set_author(name='請註冊 cookie', icon_url=user.avatar),
        try:
            notes = await client.get_notes(uid)
        except genshin.errors.DataNotPublic:
            return errEmbed(
                '輸入 `/stuck` 來獲取更多資訊').set_author(name='資料不公開', icon_url=user.avatar), False
        except Exception as e:
            return errEmbed(f'```{e}```').set_author(name='錯誤', icon_url=user.avatar), False
        else:
            if resin_notification_toggle == 0:
                await c.execute('UPDATE genshin_accounts SET resin_notification_toggle = 0 WHERE user_id = ?', (user_id,))
                result = defaultEmbed()
            else:
                await c.execute('UPDATE genshin_accounts SET resin_notification_toggle = ?, resin_threshold = ? , max_notif = ? WHERE user_id = ?', (resin_notification_toggle, resin_threshold, max_notif, user_id))
                toggle_str = '開' if resin_notification_toggle == 1 else '關'
                result = defaultEmbed(
                    message=f'目前開關: {toggle_str}\n'
                    f'樹脂提醒閥值: {resin_threshold}\n'
                    f'最大提醒數量: {max_notif}'
                )
                result.set_author(name='設置成功', icon_url=user.avatar)
            await self.db.commit()
        return result, True

    async def redeemCode(self, user_id: int, code: str):
        client, uid, only_uid, user = await self.getUserCookie(user_id)
        if only_uid:
            return errEmbed(message='使用 `/cookie` 指令來註冊').set_author(name='請註冊 cookie', icon_url=user.avatar),
        try:
            await client.redeem_code(code)
        except genshin.errors.InvalidCookies:
            return errEmbed(message=
                '你並非使用 cookie v2.0!\n'
                '輸入 `/cookie` 來註冊 cookie v2.0\n'
                '(之前註冊過的用戶需要再次註冊, 真的非常抱歉)'
            ).set_author(name='設置 cookie v2.0', icon_url=user.avatar), False
        except genshin.errors.RedemptionClaimed:
            return errEmbed().set_author(name='你已經兌換過這個兌換碼了!', icon_url=user.avatar), False
        except genshin.errors.GenshinException:
            return errEmbed().set_author(name='兌換碼無效', icon_url=user.avatar), False
        else:
            return defaultEmbed(message=f'兌換碼: {code}').set_author(name='兌換成功', icon_url=user.avatar), True

    async def getUserCookie(self, user_id: int):
        user = self.bot.get_user(user_id)
        c: aiosqlite.Cursor = await self.db.cursor()
        seria_id = 224441463897849856
        await c.execute('SELECT ltuid FROM genshin_accounts WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        if result is None or result[0] is None:
            await c.execute('SELECT ltuid FROM genshin_accounts WHERE user_id = ?', (seria_id,))
            ltuid = (await c.fetchone())[0]
            await c.execute('SELECT ltoken FROM genshin_accounts WHERE user_id = ?', (seria_id,))
            ltoken = (await c.fetchone())[0]
            await c.execute('SELECT cookie_token FROM genshin_accounts WHERE user_id = ?', (seria_id,))
            cookie_token = (await c.fetchone())[0]
            await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (user_id,))
            uid = await c.fetchone()
            uid = uid[0]
            client = genshin.Client()
            client.set_cookies(ltuid=ltuid, ltoken=ltoken,
                               account_id=ltuid, cookie_token=cookie_token)
            client.lang = "zh-tw"
            client.default_game = genshin.Game.GENSHIN
            client.uids[genshin.Game.GENSHIN] = uid
            only_uid = True
        else:
            await c.execute('SELECT ltoken FROM genshin_accounts WHERE user_id = ?', (user_id,))
            ltoken = (await c.fetchone())[0]
            await c.execute('SELECT cookie_token FROM genshin_accounts WHERE user_id = ?', (user_id,))
            cookie_token = (await c.fetchone())[0]
            await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (user_id,))
            uid = await c.fetchone()
            uid = uid[0]
            client = genshin.Client()
            client.set_cookies(
                ltuid=result[0], ltoken=ltoken, account_id=result[0], cookie_token=cookie_token)
            client.lang = "zh-tw"
            client.default_game = genshin.Game.GENSHIN
            client.uids[genshin.Game.GENSHIN] = uid
            only_uid = False
        return client, uid, only_uid, user
