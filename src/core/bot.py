import discord
import os

from discord.ext import commands
from discord.ui import Item
from dotenv import load_dotenv

from typing import (
    List,
    Tuple
)

from core.functions import (
    load_extension,
)

from core.database import (
    Database
)

from core.configs import (
    Setting,
)

from core.item import (
    Button,
    Select,
)

load_dotenv()

class BotBuildError(BaseException):
    pass

class Bot(commands.Bot):
    def __init__(self,command_prefix="!", description=None, setting_path="setting", *args, **options):
        super().__init__(command_prefix, description, *args, **options)

        self.setting = Setting(setting_path)

        self.database_path = self.setting.database.get("path","bot.db")
        self.database = Database(self.database_path)

        self.token:str = os.getenv("TOKEN")

        self.version = self.setting.general.get("version", [0, 0, 0])
        self.avatar = self.setting.general.get("avatar_url", "")
        self.id = self.setting.general.get("id",0)

        self.cooldown = self.setting.managements.get("cooldown", [0, 0, 0])
        self.vips = self.setting.managements.get("vips", [0, 0, 0])

    def is_administrator(self, ctx:commands.Context):
        return ctx.author.guild_permissions.administrator or ctx.author.id in self.vips

    def is_available_channel(self, ctx:commands.Context):
        return ctx.channel.id in self.setting.checks["channel"]

    def is_test_channel(self, ctx:commands.Context):
        return ctx.channel.id in self.setting.checks["test_channel"]

    def is_commands_overload(self):
        data = [raw[0] for raw in self.setting.commands]

        for n in data:
            if data.count(n) > 1:
                return True

        return False

    def reload_setting(self, path:str = None):
        self.setting = Setting(self.setting.path) if not path else Setting(path)
        return self.setting

    def get_custom_commands(self, name:str) -> List[Tuple[str, dict]]: 
        return list(filter(lambda x:x[0] == name, self.setting.commands))

    def get_buttons_from_dict(self, dict) -> List[Button]: 
        return [Button.from_dict(data) for data in dict["view"]["items"]["button"]]

    def get_selects_from_dict(self, dict) -> List[Select]:
        return [Select.from_dict(data) for data in dict["view"]["items"]["select"]]

    def get_items_from_dict(self, dict) -> List[Item]:
        return [*self.get_buttons_from_dict(dict), *self.get_selects_from_dict(dict)]

    async def delete_after_sent(self, ctx:commands.Context, msg:discord.Message, sec:float = 5.0):
        await ctx.message.delete()
        await msg.delete(delay=sec)

    def setup(self):
        "setup the bot"

        [load_extension(self,folder) for folder in self.setting.cog.get("folder", [])]

        if self.setting.general["version"][0] < 1:
            self.add_check(self.is_test_channel)

        if self.is_commands_overload():
            raise BotBuildError("this bot have too many commands.")

        @self.command()
        @commands.check(self.is_administrator)
        async def load(ctx:commands.Context, extension:str = None, folder:str = "commands"):
            load_extension(self, folder) if not extension else self.load_extension(f"{folder}.{extension}")
            msg = await ctx.reply("loading end!")
            await self.delete_after_sent(ctx, msg)
            
        @self.command()
        @commands.check(self.is_administrator)
        async def unload(ctx:commands.Context, extension:str = None, folder:str = "commands"):
            load_extension(self, folder, "unload") if not extension else self.unload_extension(f"{folder}.{extension}")
            msg = await ctx.reply("unloading end!")
            await self.delete_after_sent(ctx, msg)

        @self.command()
        @commands.check(self.is_administrator)
        async def reload(ctx:commands.Context, extension:str = None, folder:str = "commands"):
            load_extension(self, folder, "reload") if not extension else self.reload_extension(f"{folder}.{extension}")
            msg = await ctx.reply("reloading end!")
            await self.delete_after_sent(ctx, msg)

        @commands.command(name="reload-setting")
        async def reload_setting(ctx:commands.Context,):
            self.reload_setting()
            msg = await ctx.reply("reloading setting end!")
            await self.delete_after_sent(ctx, msg)
    
class CogExtension(discord.Cog):
    def __init__(self, bot:Bot) -> None:
        self.bot = bot