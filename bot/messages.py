import random
from datetime import datetime, timezone

_SHAME_POOL = [
    "Ahò {shamer}! 'Sto link l'ha già messo {og_poster} {time_ago}! La vergogna, la disonore, il fallimento! 🤌",
    "Madonna {shamer}, 'sto link è vecchio come il pane duro! {og_poster} ce l'ha già buttato qui {time_ago}. Svegliati! 🫵",
    "{shamer} RIPROPONE con sfacciataggine cosmica il link già postato da {og_poster} {time_ago}. Il Consiglio dei Saggi è convocato. 🏛️",
    "Zio {shamer}! Ma stai dormendo? {og_poster} l'ha già condiviso {time_ago}! Leggi la chat prima di postare, cribbio! 🤦",
    "NOTIZIA FLASH: {shamer} ha appena riscoperto qualcosa che {og_poster} aveva già trovato {time_ago}. Applausi. 👏 (ma non buoni)",
    "O {shamer}, figlio mio perduto... questo link già camminava per la chat grazie a {og_poster} {time_ago}. La storia si ripete sempre con te. 🙏",
    "E anche oggi {shamer} ci delizia con un classico già visto. {og_poster} era avanti {time_ago}. Tu arrivi sempre dopo, eh? ⏰",
    "Caro {shamer}, ti informo con dispiacere che {og_poster} ha già illuminato questo gruppo con tale contenuto {time_ago}. Benvenuto nel passato. 🏺",
    "{shamer} vs il resto del gruppo: 0-1. {og_poster} aveva già vinto {time_ago} con questo link. Meglio tardi che mai... forse. ⚽",
    "Gesù, Giuseppe e Maria! {shamer} posta di nuovo quello che {og_poster} aveva già condiviso {time_ago}! Questa è una truffa ai danni del gruppo! 🚨",
    "Il Ministero della Novità dichiara: il link di {shamer} è SCADUTO. Prima scadenza: {time_ago}, a cura di {og_poster}. 📋",
    "Ma che mi combini {shamer}? Stiamo qui a guardare un ripetuto? {og_poster} ci aveva già fatto questo regalo {time_ago}. Vergogna! 😤",
    "ALLERTA COPINCOLLA: {shamer} ha attivato il protocollo già-visto. Operatore originale: {og_poster}, {time_ago}. Situazione sotto controllo. 🚔",
    "Egregio {shamer}, la presente per comunicarLe che il suddetto link fu depositato agli atti da {og_poster} in data {time_ago}. Cordiali saluti, Zio Tackus. 📜",
    "Incredibile ma vero: {shamer} ha trovato esattamente lo stesso link che {og_poster} aveva già trovato {time_ago}. Coincidenza? Non credo. 🕵️",
    "💀 R.I.P. alla creatività di {shamer} 💀\nPresente fin dal primo post di {og_poster}, {time_ago}. Una vita vissuta senza scroll. 🪦",
    "{shamer} entra in campo con un link del {time_ago}! Ma {og_poster} era già passato da qui! Fuorigioco! 🚩",
    "Cara chat, {shamer} ci ha appena dimostrato di non aver letto nulla da {time_ago} in poi. Quando {og_poster} postò questo capolavoro, {shamer} doveva essere in letargo. 🐻",
    "Per l'ennesima volta in assoluto: {shamer} riposta roba già postata. {og_poster} ringrazia per la pubblicità. {time_ago} ormai. 📢",
    "🎺 *squillo di trombe* 🎺\nIl grande {shamer} ci presenta... qualcosa che {og_poster} aveva già condiviso {time_ago}. Avanti il prossimo. 🎭",
]

WELCOME_MESSAGE = (
    "Ciao a tutti! 👋 Sono Zio Tackus, il guardiano dei link di questa chat.\n\n"
    "Il mio compito è semplice: tenere traccia di tutti i link che postate "
    "e smascherare senza pietà chiunque riposti qualcosa di già visto. 😤\n\n"
    "Cosa posso fare:\n"
    "• Rilevare automaticamente i link duplicati (YouTube, Instagram, Facebook, 9gag, e altri)\n"
    "• /stats — classifica dei link postati da ciascun membro\n"
    "• /hall\\_of\\_shame — il podio dei copincollatori seriali 🏆\n\n"
    "Nota: se volete che io ricordi i link postati prima del mio arrivo, "
    "chiedete all'admin di seguire le istruzioni nel README per importare "
    "la cronologia della chat. 📂\n\n"
    "Che la vergogna sia con voi. 🤌"
)


def pick_shame_message(shamer: str, og_poster: str, posted_at_utc: str) -> str:
    dt = datetime.fromisoformat(posted_at_utc.replace("Z", "+00:00"))
    time_ago = _format_time_ago(dt)
    template = random.choice(_SHAME_POOL)
    return template.format(shamer=shamer, og_poster=og_poster, time_ago=time_ago)


def _format_time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return "pochissimo fa"
    if total_seconds < 3600:
        m = total_seconds // 60
        return f"{m} minuto fa" if m == 1 else f"{m} minuti fa"
    if total_seconds < 86400:
        h = total_seconds // 3600
        return "un'ora fa" if h == 1 else f"{h} ore fa"
    days = delta.days
    if days == 1:
        return "ieri"
    if days < 30:
        return f"{days} giorni fa"
    if days < 365:
        m = days // 30
        return f"{m} mese fa" if m == 1 else f"{m} mesi fa"
    y = days // 365
    return f"{y} anno fa" if y == 1 else f"{y} anni fa"


def display_name(username: str | None, first_name: str) -> str:
    if username:
        return f"@{username}"
    return first_name
