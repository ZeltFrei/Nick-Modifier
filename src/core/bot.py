import discord
import os

from datetime import datetime
from dotenv import load_dotenv

from discord.ext import commands
from discord.ui import Item

from core.functions import load_extension
from core.database import Database
from core.configs import Setting
from core.embed import Embed

from core.item import View
from core.modal import Modal

from typing import (
    List,
    Dict
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

    def _get_custom_commands_config(self, name: str) -> dict: 
        return list(filter(lambda x:x[0] == name, self.setting.commands))[0][1]

    def get_vips(self):
        return Database(self.database_path).primary_users

    def get_database(self):
        return Database(self.database_path)

    def get_user_cooldown(self, id: int | str): 
        return None if str(id) not in self.database.user_cooldown else datetime(**self.database.user_cooldown.get(str(id)))

    def get_custom_id(self, name: str, data: dict = None) -> List[str]:

        if not data:
            data = self._get_custom_commands_config(name)

        result = []

        for k,v in data["view"]["items"].items():
            result += [i["label"] for i in v]

        return result

    async def response(self, interaction: discord.Interaction, data: dict):

        if data.get("embed"):
            embed = Embed.from_dict(data["embed"]) 
        if data.get("view"):
            view = View.from_dict(data["view"])
        if data.get("modal"):
            modal = Modal.from_dict(data["modal"])
        if modal:
            await interaction.response.send_modal(modal)
        if embed or view:
            await interaction.response.send_message(embed=embed, view=view)

    def get_select_interaction_response(self, interaction: discord.Interaction, data: dict):
        return {k: self.response(interaction, v) for k, v in data.items()}

    def get_interaction_responses(self, interaction: discord.Interaction, key: str):
        config: dict[str, dict] = self._get_custom_commands_config(key)["interaction"]
        
        return {k: self.response(interaction, v) for k, v in config.items()}


    def get_command_with_custom_id(self) -> List[Dict[str, List[str]]]:
        return [{n: self.get_custom_id(n, v)} for n,v in self.setting.commands]

    def is_administrator(self, ctx: commands.Context):
        return ctx.author.guild_permissions.administrator or ctx.author.id in self.get_vips()

    def is_available_channel(self, ctx: commands.Context):
        return ctx.channel.id in self.setting.checks["channel"]

    def is_test_channel(self, ctx: commands.Context):
        return ctx.channel.id in self.setting.checks["test_channel"]

    def is_commands_overload(self):
        data = [raw[0] for raw in self.setting.commands]

        for n in data:
            if data.count(n) > 1:
                return True

        return False

    def build_custom_command(self, config_key: str, name: str, description: str):
        
        async def callback(ctx):
            config = self._get_custom_commands_config(config_key)
            embed = Embed.from_dict(config["embed"])

            view = View.from_dict(config["view"])

            if isinstance(ctx, commands.Context):
                await ctx.reply(
                    embed=embed,
                    view=view,
                    mention_author=False
                )

            elif isinstance(ctx, discord.ApplicationContext):
                await ctx.response.send_message(
                    embed=embed,
                    view=view
                )

        @self.application_command(name=name, description=description)
        async def application(ctx):
            await callback(ctx)
            
        @self.command(name=config_key)
        async def command(ctx):
            await callback(ctx)

        return callback

    def reload_setting(self, path:str = None):
        self.setting = Setting(self.setting.path) if not path else Setting(path)
        return self.setting

    async def delete_after_sent(self, ctx: commands.Context, msg: discord.Message, sec: float = 5.0):
        await ctx.message.delete()
        await msg.delete(delay=sec)

    def setup(self):
        "setup the bot"

        [load_extension(self,folder) for folder in self.setting.cog.get("folder", [])]

        if self.setting.general["version"][0] < 1:
            self.add_check(self.is_test_channel)

        if self.is_commands_overload():
            raise BotBuildError("this bot have same name custom commands.")

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


if __name__ == "__main__":
    pass