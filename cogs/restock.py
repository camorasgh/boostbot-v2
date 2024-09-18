import disnake
from disnake.ext import commands

class Restock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(name="restock", description="Restocks tokens")
    async def restock(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        token_type: str = commands.Param(choices=["1M", "3M"]),
        file: disnake.Attachment = commands.Param(description="The file with tokens to restock")
    ):
        if not file:
            await interaction.response.send_message("Please upload a file with the tokens.")
            return

        file_path = f'assets/{token_type.lower()}_tokens.txt'
        content = await file.read()
        tokens = content.decode('utf-8').splitlines()
        with open(file_path, 'a') as f:
            for token in tokens:
                f.write(f"{token}\n")

        embed = disnake.Embed(
            title="Restock Successful",
            description=f"Successfully restocked ``{len(tokens)}`` tokens for {token_type}.",
            color=disnake.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(Restock(bot))