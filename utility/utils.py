import discord


global warningColor, purpleColor, footerAuthor, footerImage, timeOutErrorMsg, embedNoAccount, embedNoGroup, groups, whyRegister
warningColor = 0xfc5165
purpleColor = 0xa68bd3
footerAuthor = "輸入!help來獲得幫助"
footerImage = "https://i.imgur.com/DWYpYrd.jpg"
timeOutErrorMsg = "已取消當前操作, 請在30秒內回答問題"
embedNoAccount = discord.Embed(
    title="😢 該帳號不存在", description="請使用`!register`來註冊帳號, 如有疑問請@小雪", color=warningColor)
whyRegister = "• `!abyss`炫耀你的深淵傷害(或被嘲笑)\n• `!check`查看目前的派遣、樹脂、塵歌壺等狀況\n• `!char`炫耀你擁有的角色\n• `!stats`證明你是大佬\n• `!diary`看看這個月要不要課\n• `!area`炫耀探索度(或被嘲笑)\n• `!today`今天的肝還在嗎\n• 自動領取hoyolab網頁登入獎勵\n• 樹脂提醒功能(詳情請打`!dm`)"


def setFooter(embed):
    embed.set_footer(text=footerAuthor, icon_url=footerImage)

def defaultEmbed(title:str, message:str):
    return discord.Embed(title=title, description=message, color=purpleColor)

def errEmbed(title:str, message:str):
    return discord.Embed(title=title, description=message, color=warningColor)

def log(is_system:bool, is_error:bool, log_type:str, log_msg:str):
    system = "SYSTEM"
    if not is_system:
        system = "USER"
    if not is_error:
        result = f"[{system}][{log_type}] {log_msg}"
    else:
        result = f"[{system}][ERROR][{log_type}] {log_msg}"
    return result
    