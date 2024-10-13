import discord
from discord.ext import commands, tasks
import requests
import random
import asyncio
import os
import json
import re
import nacl


PREFIX = "+"  
TOKEN_FILE = "token.txt" 

SUPRA_OWNER_ID = 1254217638977077305

intents = discord.Intents.all() 

EMBED_COLOR = discord.Color.dark_purple()

# Variable pour suivre l'état de l'antibot
antibot_enabled = False

STATUTS = ["JOIN NOW", "https://discord.gg/36Zm4zASq9"]


bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

deleted_messages = {}

# Fonction pour créer un embed rouge avec le contenu donné
# Fonction pour créer un embed avec un contenu donné et une couleur optionnelle
def create_embed(content, color=EMBED_COLOR):
    embed = discord.Embed(description=content, color=color)
    return embed



# Lecture du token à partir du fichier token.txt
def load_token():
    try:
        with open(TOKEN_FILE, "r") as file:
            token = file.read().strip()
        return token
    except FileNotFoundError:
        print(f"Le fichier {TOKEN_FILE} n'a pas été trouvé.")
        return None

# Token du bot
TOKEN = load_token()

def is_whitelisted(user_id):
    # Lire les IDs whitelistés à partir du fichier
    if os.path.exists("whitelist.txt"):
        with open("whitelist.txt", "r") as f:
            whitelisted_ids = f.read().splitlines()
        return str(user_id) in whitelisted_ids
    return False


@tasks.loop(seconds=3)  # Change le statut toutes les 60 secondes
async def change_status():
    # Sélectionne un statut aléatoire
    new_status = random.choice(STATUTS)
    await bot.change_presence(activity=discord.Game(name=new_status))


@bot.command()
async def info(ctx, user_id: str = None):  # Le type d'argument est toujours str
    if user_id is None:
        # Si l'utilisateur n'a pas fourni d'ID, envoie un message d'erreur et supprime le message de la commande
        embed = create_embed("Erreur : Il manque un `user_id`.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Supprime le message de l'utilisateur
        await asyncio.sleep(5)  # Attendre 5 secondes
        await message.delete()  # Supprime le message d'erreur
        return

    try:
        # Essayer de convertir l'ID en entier
        user_id = int(user_id)
        user = await bot.fetch_user(user_id)
        
        embed = discord.Embed(title="Informations sur l'utilisateur", color=EMBED_COLOR)
        embed.add_field(name="ID", value=user.id, inline=False)
        embed.add_field(name="Nom d'utilisateur", value=user.name, inline=False)
        embed.add_field(name="Avatar", value=user.avatar if hasattr(user, 'avatar') else "N/A", inline=False)
        embed.add_field(name="Global Name", value=user.global_name if hasattr(user, 'global_name') else "N/A", inline=False)
        embed.add_field(name="Bot", value=user.bot, inline=False)
        await ctx.send(embed=embed)
    except ValueError:
        # Gérer l'erreur de conversion
        embed = create_embed("Erreur : Ce n'est pas un ID utilisateur valide.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Supprime le message de l'utilisateur
        await asyncio.sleep(5)
        await message.delete()
    except discord.NotFound:
        embed = create_embed("Utilisateur non trouvé. Assurez-vous de fournir un identifiant utilisateur valide.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Supprime le message de l'utilisateur
        await asyncio.sleep(5)
        await message.delete()
    except Exception as e:
        embed = create_embed(f"Une erreur s'est produite : {e}", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Supprime le message de l'utilisateur
        await asyncio.sleep(5)
        await message.delete()





@bot.command()
@commands.has_permissions(administrator=True)
async def changer_prefixe(ctx, prefix: str = None):
    if prefix is None:
        # Si le préfixe n'est pas fourni, envoie un message d'erreur sous forme d'embed
        embed = create_embed("Erreur : Il manque un préfixe.", color=discord.Color.red())
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    global PREFIX
    PREFIX = prefix
    bot.command_prefix = prefix

    # Envoie un message de confirmation sous forme d'embed
    embed = discord.Embed(
        title="Préfixe modifié",
        description=f"Le préfixe a été changé pour : `{prefix}`",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)


@bot.command()
async def bienvenue(ctx):
    # Vérifier si l'utilisateur a les autorisations nécessaires
    if not ctx.author.guild_permissions.administrator:
        embed = create_embed("Vous n'avez pas les autorisations nécessaires pour effectuer cette action.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Récupérer l'ID du serveur actuel
    guild_id = ctx.guild.id

    # Vérifier si le fichier welcome_config.txt existe
    if os.path.exists("welcome_config.txt"):
        try:
            # Charger les données de configuration depuis le fichier welcome_config.txt
            with open("welcome_config.txt", "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            # Si le fichier est vide ou contient un JSON invalide, initialiser config_data comme un dictionnaire vide
            config_data = {}
    else:
        # Si le fichier n'existe pas, initialiser config_data comme un dictionnaire vide
        config_data = {}

    if str(guild_id) in config_data:
        # Le serveur est déjà configuré dans welcome_config.txt
        welcome_channel_id = config_data[str(guild_id)]
        welcome_channel = ctx.guild.get_channel(welcome_channel_id)
        if welcome_channel:
            # Le salon de bienvenue est déjà défini, demander à l'utilisateur s'il veut le changer
            embed = create_embed(f"Un salon est déjà défini pour le serveur : {welcome_channel.mention}. Voulez-vous le changer pour {ctx.channel.mention} ?", color=EMBED_COLOR)
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                embed = create_embed("Temps écoulé. L'action a été annulée.", color=discord.Color.red())
                await ctx.send(embed=embed)
                await message.delete()
                return

            if str(reaction.emoji) == "✅":
                # Mettre à jour le salon de bienvenue dans welcome_config.txt
                config_data[str(guild_id)] = ctx.channel.id
                with open("welcome_config.txt", "w") as f:
                    json.dump(config_data, f)
                embed = create_embed(f"Le salon de bienvenue a été changé pour {ctx.channel.mention}.", color=EMBED_COLOR)
                await ctx.send(embed=embed)
                await message.delete()  # Supprime le message de confirmation
            else:
                embed = create_embed("Action annulée.", color=EMBED_COLOR)
                await ctx.send(embed=embed)
                await message.delete()  # Supprime le message de confirmation
                
                # Supprime le message d'action annulée après 5 secondes
                await asyncio.sleep(5)
                await ctx.message.delete()  # Supprime le message d'origine

        else:
            embed = create_embed("Salon de bienvenue introuvable.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        # Le serveur n'est pas encore configuré dans welcome_config.txt, enregistrer le salon de bienvenue
        config_data[str(guild_id)] = ctx.channel.id
        with open("welcome_config.txt", "w") as f:
            json.dump(config_data, f)
        embed = create_embed(f"Le salon de bienvenue a été configuré pour {ctx.channel.mention}.", color=EMBED_COLOR)
        await ctx.send(embed=embed)


@bot.command()
async def antibot(ctx, status: str = None):
    global antibot_enabled

    # Vérifie si l'utilisateur est le supra owner
    if ctx.author.id != SUPRA_OWNER_ID:
        embed = discord.Embed(description="❌ Vous n'êtes pas autorisé à utiliser cette commande.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Vérifier si le fichier antibot.txt existe, sinon le créer
    if not os.path.exists("antibot.txt"):
        with open("antibot.txt", "w") as f:
            json.dump({}, f)  # Créer un fichier vide

    # Charger l'état de l'antibot depuis le fichier antibot.txt
    try:
        with open("antibot.txt", "r") as f:
            antibot_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        antibot_data = {}

    if status is None:
        # Affiche le statut actuel de l'antibot
        antibot_enabled = antibot_data.get(str(ctx.guild.id), False)
        status_message = "Antibot est actuellement **activé**." if antibot_enabled else "Antibot est actuellement **désactivé**."
        embed = discord.Embed(description=status_message, color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    if status.lower() == 'on':
        antibot_enabled = True
        antibot_data[str(ctx.guild.id)] = True
        embed = discord.Embed(description="✅ Antibot est activé !", color=EMBED_COLOR)
        await ctx.send(embed=embed)
    elif status.lower() == 'off':
        antibot_enabled = False
        antibot_data[str(ctx.guild.id)] = False
        embed = discord.Embed(description="❌ Antibot est désactivé !", color=EMBED_COLOR)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="⚠️ Veuillez utiliser `antibot on`, `antibot off`, ou simplement `antibot` pour vérifier le statut.", color=EMBED_COLOR)
        await ctx.send(embed=embed)

    # Sauvegarder l'état de l'antibot dans le fichier antibot.txt
    with open("antibot.txt", "w") as f:
        json.dump(antibot_data, f)

@bot.command()
async def movebot(ctx, channel_id: int):
    # Vérifie si l'utilisateur est le supra owner
    if ctx.author.id != SUPRA_OWNER_ID:
        embed = discord.Embed(description="❌ Vous n'êtes pas autorisé à utiliser cette commande.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Récupérer le salon vocal avec l'ID fourni
    channel = ctx.guild.get_channel(channel_id)

    # Vérifier si le salon existe et est un salon vocal
    if not isinstance(channel, discord.VoiceChannel):
        embed = discord.Embed(description="⚠️ L'ID fourni ne correspond pas à un salon vocal.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Vérifie si le bot est déjà dans un canal vocal
    if ctx.voice_client is not None:
        # Déplace le bot vers le canal vocal spécifié
        await ctx.voice_client.move_to(channel)
        embed = discord.Embed(description=f"✅ Le bot a été déplacé vers {channel.mention}.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
    else:
        # Si le bot n'est pas connecté, il doit se connecter au canal vocal
        embed = discord.Embed(description="⚠️ Le bot n'est pas connecté à un canal vocal. Veuillez le connecter d'abord.", color=0xff0000)
        await ctx.send(embed=embed)
@bot.command()
async def connect(ctx, channel_id: int):
    # Vérifie si l'utilisateur est le supra owner
    if ctx.author.id != SUPRA_OWNER_ID:
        embed = discord.Embed(description="❌ Vous n'êtes pas autorisé à utiliser cette commande.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Récupérer le salon vocal avec l'ID fourni
    channel = ctx.guild.get_channel(channel_id)

    # Vérifier si le salon existe et est un salon vocal
    if not isinstance(channel, discord.VoiceChannel):
        embed = discord.Embed(description="⚠️ L'ID fourni ne correspond pas à un salon vocal.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Vérifie si le bot est déjà connecté à un canal vocal
    if ctx.voice_client is not None:
        embed = discord.Embed(description="⚠️ Le bot est déjà connecté à un salon vocal.", color=0xff0000)
        await ctx.send(embed=embed)
        return

    # Connecte le bot au salon vocal
    await channel.connect()
    embed = discord.Embed(description=f"✅ Le bot a été connecté au salon vocal {channel.mention}.", color=EMBED_COLOR)
    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    # Vérifier si le serveur est configuré dans welcome_config.txt
    try:
        with open("welcome_config.txt", "r") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}

    guild_id = member.guild.id
    if str(guild_id) in config_data:
        welcome_channel_id = config_data[str(guild_id)]
        welcome_channel = member.guild.get_channel(welcome_channel_id)
        if welcome_channel:
            embed = discord.Embed(description=f"Bienvenue {member.mention} dans {member.guild.name}!", color=0x00ff00)
            await welcome_channel.send(embed=embed)

    # Vérifier si l'antibot est activé
    global antibot_enabled
    if antibot_enabled and member.bot:
        # Banni le bot
        try:
            await member.ban(reason="Bot détecté par l'antibot.")
            print(f"{member.name} a été banni car c'était un bot.")
        except discord.Forbidden:
            print("Je n'ai pas les permissions nécessaires pour bannir ce membre.")
        except discord.HTTPException:
            print("Erreur lors de la tentative de bannissement de ce membre.")



@bot.command()
async def geoip(ctx, ip_address: str = None):
    if ip_address is None:
        embed = create_embed("Erreur : Il manque une adresse IP.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    ip_info_url = f"https://ipinfo.io/{ip_address}/json"
    try:
        response = requests.get(ip_info_url)
        ip_info_data = response.json()

        embed = discord.Embed(title=f"Informations sur l'adresse IP : {ip_address}", color=EMBED_COLOR)
        embed.add_field(name="IP", value=ip_info_data.get('ip', 'N/A'), inline=False)
        embed.add_field(name="Pays", value=ip_info_data.get('country', 'N/A'), inline=True)
        embed.add_field(name="Région", value=ip_info_data.get('region', 'N/A'), inline=True)
        embed.add_field(name="Ville", value=ip_info_data.get('city', 'N/A'), inline=True)
        embed.add_field(name="Opérateurs", value=ip_info_data.get('org', 'N/A'), inline=False)

        loc = ip_info_data.get('loc', '').split(',')
        if len(loc) == 2:
            latitude, longitude = loc
            embed.add_field(name="Adresse Approximative", value=f"{latitude}, {longitude}", inline=True)
        
        vpn_status = "Oui" if ip_info_data.get('vpn') else "Non"
        embed.add_field(name="VPN", value=vpn_status, inline=True)

        await ctx.send(embed=embed)

        # Envoie un message privé avec les informations
        dm_embed = discord.Embed(title="Regarde tes DM !", description="Les informations sur l'adresse IP ont été envoyées en message privé.", color=EMBED_COLOR)
        await ctx.send(embed=dm_embed)
        await ctx.author.send(embed=embed)

    except requests.exceptions.RequestException as e:
        embed = create_embed(f"Erreur lors de la récupération des informations : {e}", color=discord.Color.red())
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed(f"Une erreur s'est produite : {e}", color=discord.Color.red())
        await ctx.send(embed=embed)



@bot.command()
async def search(ctx, word: str = None):
    if word is None:
        embed = create_embed("Erreur : Il manque un mot à rechercher.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    # Lire le chemin d'accès depuis le fichier
    try:
        with open("search_path.txt", "r") as f:
            directory = f.read().strip()
    except FileNotFoundError:
        embed = create_embed("Erreur : Le chemin d'accès n'est pas défini. Veuillez utiliser `setsearchpath` pour le définir.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    # Vérifie si le chemin d'accès existe
    if not os.path.exists(directory):
        embed = create_embed("Erreur : Le chemin d'accès spécifié n'existe pas.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    files_with_word = []

    # Parcourir tous les fichiers dans le dossier
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if word.lower() in line.lower():
                        files_with_word.append((filename, line.strip()))

    if files_with_word:
        # Créer un embed pour les résultats
        embed = discord.Embed(title=f"Résultats de la recherche pour '{word}':", color=EMBED_COLOR)
        for filename, line in files_with_word:
            formatted_line = f"||{line}||"  # Mettre la ligne en spoiler
            embed.add_field(name=f"Fichier : {filename}", value=formatted_line, inline=False)

        # Envoyer les résultats par message privé
        try:
            await ctx.author.send(embed=embed)
            confirmation_embed = create_embed("Les résultats ont été envoyés en message privé !", color=EMBED_COLOR)
            await ctx.send(embed=confirmation_embed)
        except discord.Forbidden:
            embed = create_embed("Erreur : Je ne peux pas vous envoyer de message privé. Vérifiez vos paramètres de confidentialité.", color=discord.Color.red())
            await ctx.send(embed=embed)
    else:
        embed = create_embed(f"Aucun résultat trouvé pour '{word}'.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()


@bot.command()
async def ping(ctx):
    # Envoie un message pour le temps de latence
    embed = create_embed("Pinging...", color=EMBED_COLOR)
    message = await ctx.send(embed=embed)

    # Calcule la latence
    latency = round(bot.latency * 1000)  # Convertir en ms

    # Créer un nouvel embed avec le temps de latence
    embed = create_embed(f"🏓 Pong ! Latence : `{latency} ms`", color=EMBED_COLOR)

    # Édite le message original pour afficher la latence
    await message.edit(embed=embed)


@bot.command()
async def invite(ctx):
    embed = discord.Embed(
        title="Ajouter Le Bot",
        description="[Cliquez ici pour inviter le bot sur votre serveur](https://discord.com/oauth2/authorize?client_id=1294568841619439719&permissions=8&scope=bot)",
        color=EMBED_COLOR
    )
    embed.set_footer(text="Merci d'utiliser notre bot !")
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Bot prêt en tant que {bot.user}')
    change_status.start()  # Démarre la tâche de changement de statut

@bot.command()
async def clearmp(ctx, user: discord.User = None):
    # Vérifie si l'utilisateur est whitelisted ou si c'est le supra owner
    if not is_whitelisted(ctx.author.id) and ctx.author.id != SUPRA_OWNER_ID:
        embed = create_embed("Vous n'avez pas les autorisations nécessaires pour utiliser cette commande.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Si aucun utilisateur n'est mentionné, supprime les MP du bot pour l'utilisateur qui a appelé la commande
    if user is None:
        user = ctx.author

    # Vérifie si la commande est utilisée dans un canal de texte
    if isinstance(ctx.channel, discord.DMChannel):
        embed = create_embed("Cette commande ne peut pas être utilisée dans un message privé.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    try:
        deleted_count = 0
        # Envoyer un message de confirmation avant de commencer à supprimer
        confirmation_embed = create_embed(f"Suppression des messages privés de {user.name}...", color=EMBED_COLOR)
        confirmation_message = await ctx.send(embed=confirmation_embed)

        # Parcourir l'historique des messages en DM de l'utilisateur
        user_dm_channel = await user.create_dm()
        async for message in user_dm_channel.history(limit=None):
            if message.author == bot.user:
                await message.delete()
                deleted_count += 1

        # Envoie un message de confirmation indiquant combien de messages ont été supprimés
        embed = create_embed(f"{deleted_count} message(s) du bot pour {user.name} ont été supprimés.", color=EMBED_COLOR)
        await ctx.send(embed=embed)

        # Supprime le message de commande après un court délai
        await asyncio.sleep(2)
        await ctx.message.delete()
        await confirmation_message.delete()

    except Exception as e:
        # Gérer les exceptions et envoyer un message d'erreur
        embed = create_embed(f"Une erreur s'est produite lors de la suppression des messages : {e}", color=discord.Color.red())
        await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def sendmp(ctx, user: discord.User = None, *, message: str = None):
    if user is None:
        # Si l'utilisateur n'est pas mentionné ou ID non fourni
        embed = discord.Embed(
            description="Erreur : Vous devez mentionner un utilisateur ou fournir un ID valide.",
            color=discord.Color.red()
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
        return

    if message is None:
        # Si le message n'est pas fourni
        embed = discord.Embed(
            description="Erreur : Vous devez fournir un message à envoyer.",
            color=discord.Color.red()
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
        return

    # Vérifie si l'utilisateur fait partie d'un des serveurs du bot
    is_in_guild = False
    for guild in bot.guilds:
        if guild.get_member(user.id):
            is_in_guild = True
            break

    if not is_in_guild:
        # Si l'utilisateur n'est pas dans les serveurs où le bot est présent
        embed = discord.Embed(
            description="Impossible d'envoyer un message privé : L'utilisateur n'est pas présent dans un des serveurs.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    try:
        # Envoie le message privé à l'utilisateur
        await user.send(message)

        # Confirmation dans le salon sous forme d'embed
        embed = discord.Embed(
            description=f"Message envoyé à {user.name} en message privé : {message}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)

    except discord.Forbidden:
        # Si l'utilisateur bloque les messages privés
        embed = discord.Embed(
            description="Erreur : Impossible d'envoyer un message privé à cet utilisateur (bloqué ou désactivé).",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        # Pour d'autres erreurs inattendues
        embed = discord.Embed(
            description=f"Une erreur s'est produite : {e}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


antilink_status = {}  # Dictionnaire pour stocker l'état de l'antilink par serveur

# Commande pour activer/désactiver l'antilink
@bot.command()
@commands.has_permissions(administrator=True)
async def antilink(ctx, status: str = None):
    guild_id = ctx.guild.id  # ID du serveur actuel
    if status is None:
        # Si aucun argument n'est passé, renvoyer l'état actuel
        current_status = antilink_status.get(guild_id, "off")
        embed = discord.Embed(
            title="État de l'antilink",
            description=f"L'antilink est actuellement : `{current_status}`.",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    elif status.lower() == "on":
        # Activer l'antilink
        antilink_status[guild_id] = "on"
        embed = discord.Embed(
            title="Antilink activé",
            description="L'antilink a été activé avec succès.",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    elif status.lower() == "off":
        # Désactiver l'antilink
        antilink_status[guild_id] = "off"
        embed = discord.Embed(
            title="Antilink désactivé",
            description="L'antilink a été désactivé.",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    else:
        # Si l'utilisateur entre autre chose que "on" ou "off"
        embed = discord.Embed(
            title="Erreur de commande",
            description="Utilisez `+antilink on` ou `+antilink off` pour activer ou désactiver l'antilink.",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)

# Expression régulière pour détecter n'importe quel lien
url_regex = re.compile(
    r"(https?://\S+|www\.\S+|discord\.gg/\S+|discordapp\.com/invite/\S+)"
)

@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ne pas traiter les messages des bots
    
    guild_id = message.guild.id
    antilink_active = antilink_status.get(guild_id, "off")
    
    # Vérifie si l'utilisateur est whitelisté avant de supprimer le lien
    if antilink_active == "on" and not is_whitelisted(message.author.id):
        if url_regex.search(message.content):
            await message.delete()  # Supprime le message
            embed = discord.Embed(
                title="Lien détecté",
                description=f"{message.author.mention}, les liens ne sont pas autorisés ici.",
                color=EMBED_COLOR
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

    await bot.process_commands(message)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx):
    await ctx.message.delete()  # Supprime le message de l'utilisateur
    message_content = ctx.message.content[len(ctx.prefix) + len("say "):]  # Récupère le texte après la commande
    await ctx.send(message_content)  # Envoie le texte spécifié par l'utilisateur



@bot.event
async def on_message_delete(message):
    deleted_messages[message.channel.id] = (message.content, message.author)

@bot.command()
async def snipe(ctx):
    channel_id = ctx.channel.id
    if channel_id in deleted_messages:
        content, author = deleted_messages[channel_id]
        embed = discord.Embed(color=EMBED_COLOR)
        embed.add_field(name="Message supprimé :", value=content, inline=False)
        embed.set_footer(text=f"Supprimé par : {author.display_name}")
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="Aucun message supprimé n'a été trouvé.", color=EMBED_COLOR)
        await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx):
    await ctx.channel.purge(limit=101)  # Limite de 101 pour inclure la commande elle-même
    embed = create_embed("Les 100 derniers messages ont été effacés.")
    await ctx.send(embed=embed, delete_after=5)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    embed = create_embed(f'{member.mention} a été banni.')
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    embed = create_embed(f'{member.mention} a été expulsé.')
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, delay: int):
    try:
        await ctx.channel.edit(slowmode_delay=delay)
        embed = discord.Embed(description=f"Mode lent activé. Limite de {delay} secondes entre chaque message.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(description=f"Erreur lors de l'activation du mode lent : {e}", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    # Récupérer les autorisations actuelles pour le rôle @everyone
    channel_permissions = ctx.channel.overwrites_for(ctx.guild.default_role)
    # Modifier uniquement l'autorisation d'envoi de messages
    channel_permissions.send_messages = False
    # Appliquer uniquement la modification à l'autorisation d'envoi de messages
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=channel_permissions)

    embed = create_embed("Ce salon a été verrouillé.")
    await ctx.send(embed=embed)

@bot.command()
async def servers(ctx):
    if ctx.author.id != SUPRA_OWNER_ID:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return



    # Créer une liste de chaînes contenant les noms des serveurs et leurs ID
    guilds_info = [f"{guild.name} (ID: {guild.id})" for guild in bot.guilds]

    # Créer un embed avec la liste des serveurs et leurs ID
    embed = discord.Embed(title="Serveurs où je suis présent :", color=EMBED_COLOR)
    embed.description = "\n".join(guilds_info)

    # Envoyer l'embed dans le canal où la commande a été utilisée
    await ctx.send(embed=embed)




@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    # Récupérer les autorisations actuelles pour le rôle @everyone
    channel_permissions = ctx.channel.overwrites_for(ctx.guild.default_role)
    # Rétablir l'autorisation d'envoi de messages
    channel_permissions.send_messages = True
    # Appliquer uniquement la modification à l'autorisation d'envoi de messages
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=channel_permissions)

    embed = create_embed("Ce salon a été déverrouillé.")
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def setpicture(ctx, url):
    if ctx.author.id != SUPRA_OWNER_ID:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return


    try:
        response = requests.get(url)
        await bot.user.edit(avatar=response.content)
        embed = discord.Embed(description="La photo de profil a été mise à jour.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
    except Exception as e:
        pass  # Ne rien faire en cas d'erreur

@bot.command()
@commands.is_owner()
async def setname(ctx, *, name):
    if ctx.author.id != SUPRA_OWNER_ID:
        await ctx.send("Vous n'êtes pas autorisé à utiliser cette commande.")
        return
    try:
        await bot.user.edit(username=name)
        await ctx.send(f"Le nom du bot a été changé pour {name}.")
    except Exception as e:
        await ctx.send(f"Erreur lors du changement du nom du bot : {e}")

@bot.command()
async def dmall(ctx, *, message_content: str = None):
    # Vérifie si l'utilisateur est le supra owner
    if ctx.author.id != SUPRA_OWNER_ID:
        embed = create_embed("❌ Vous n'êtes pas autorisé à utiliser cette commande.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Vérifie si un message a été fourni
    if message_content is None:
        embed = create_embed("Erreur : Il manque un message à envoyer.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    success_count = 0
    failure_count = 0

    # Obtenir tous les membres du serveur
    members = ctx.guild.members

    # Message de confirmation avant l'envoi
    confirmation_embed = create_embed(f"Envoi du message à tous les membres...", color=EMBED_COLOR)
    confirmation_message = await ctx.send(embed=confirmation_embed)

    for member in members:
        try:
            if not member.bot:  # Ignorer les bots
                await member.send(message_content)  # Envoyer le message
                success_count += 1
                print(f"[+] Message envoyé à {member.name}")
                await asyncio.sleep(1)  # Délai pour éviter le spam
        except discord.Forbidden:
            failure_count += 1
            print(f"[-] Impossible d'envoyer un message à {member.name}")

    # Résumé des résultats
    embed = create_embed(
        f"`✅` **DMall terminé !**\n"
        f"Un message a été envoyé à `{success_count}` utilisateurs.\n"
        f"`{failure_count}` échecs.",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

    # Supprimer le message de confirmation après quelques secondes
    await asyncio.sleep(5)
    await confirmation_message.delete()


@bot.command()
async def setsearchpath(ctx, *, new_path: str = None):
    # Vérifie si l'utilisateur est le supra owner
    if ctx.author.id != SUPRA_OWNER_ID:
        embed = create_embed("❌ Vous n'êtes pas autorisé à utiliser cette commande.", color=EMBED_COLOR)
        await ctx.send(embed=embed)
        return

    # Vérifie si un nouveau chemin a été fourni
    if new_path is None:
        embed = create_embed("Erreur : Veuillez fournir un nouveau chemin d'accès.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    # Vérifie si le chemin d'accès existe
    if not os.path.exists(new_path):
        embed = create_embed("Erreur : Le chemin d'accès spécifié n'existe pas.", color=EMBED_COLOR)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)  # Supprime le message après 5 secondes
        await message.delete()
        return

    # Enregistrer le nouveau chemin d'accès dans un fichier
    with open("search_path.txt", "w") as f:
        f.write(new_path)

    embed = create_embed(f"Le chemin d'accès pour la recherche a été modifié en : `{new_path}`", color=EMBED_COLOR)
    await ctx.send(embed=embed)


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Liste des commandes disponibles :", color=EMBED_COLOR)
    commands_list = [f"{PREFIX}{command.name}" for command in bot.commands]
    embed.add_field(name="Commandes :", value="\n".join(commands_list), inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ne rien faire si la commande n'est pas trouvée
    else:
        embed = create_embed("Une erreur s'est produite lors de l'exécution de la commande.")
        await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def wl(ctx, user_id: int = None):  # user_id est maintenant optionnel
    if user_id is None:
        # Si l'ID est manquant, envoie un embed d'erreur
        embed = discord.Embed(description="Erreur : Il manque un `user_id`.", color=discord.Color.red())
        await ctx.send(embed=embed)
    else:
        try:
            # Vérifie si le fichier existe, sinon le crée
            if not os.path.exists("whitelist.txt"):
                with open("whitelist.txt", "w") as f:
                    pass  # Crée le fichier s'il n'existe pas

            # Ajoute l'ID de l'utilisateur à la whitelist
            with open("whitelist.txt", "a") as f:
                f.write(str(user_id) + "\n")

            embed = discord.Embed(description=f"L'utilisateur avec l'ID {user_id} a été ajouté à la whitelist.", color=EMBED_COLOR)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Une erreur s'est produite : {e}")



# Ajout de la commande +whiteliste pour afficher tous les IDs whitelistés
@bot.command()
@commands.is_owner()
async def whiteliste(ctx):
    try:
        # Vérifie si le fichier existe, sinon le crée
        if not os.path.exists("whitelist.txt"):
            with open("whitelist.txt", "w") as f:
                pass  # Crée simplement le fichier sans rien écrire

        # Lire les IDs dans le fichier whitelist.txt
        with open("whitelist.txt", "r") as f:
            whitelisted_ids = f.read().splitlines()

        if whitelisted_ids:
            embed = discord.Embed(title="IDs whitelistés :", description="\n".join(whitelisted_ids), color=EMBED_COLOR)
        else:
            embed = discord.Embed(description="Aucun utilisateur n'est whitelisté pour le moment.", color=EMBED_COLOR)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Une erreur s'est produite : {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ne rien faire si la commande n'est pas trouvée
    elif isinstance(error, commands.MissingPermissions):
        embed = create_embed("Vous n'avez pas les autorisations nécessaires pour exécuter cette commande.")
        await ctx.send(embed=embed, delete_after=3)
    else:
        print(f"Une erreur s'est produite lors de l'exécution de la commande : {error}")


# Lancement du bot
bot.run(TOKEN)