# MyHealth

Een Flask-website voor voeding, fitness en dagelijkse energiebalans. Je kunt producten en maaltijden beheren, voeding per dag vastleggen, trainingen registreren en persoonlijke overzichten bekijken.

Onder **MyHealth** kun je per datum vastleggen wat je bij ontbijt, lunch, avondeten en als tussendoortje hebt gegeten. Je kunt losse producten of complete opgeslagen maaltijden toevoegen en een zelfgekozen periode als PDF exporteren.

Producten worden in een doorzoekbare catalogus per categorie weergegeven. Bij een nieuw product kun je een bestaande categorie selecteren of zelf een nieuwe categorienaam typen. Bestaande databases krijgen de categorie-indeling automatisch bij de eerste start na deze update.

De productcategorie **Overig** is altijd beschikbaar. Voor oefeningen zijn **Benen**, **Borst**, **Rug**, **Triceps**, **Biceps** en **Schouders** de standaardcategorieën. Bij een nieuwe oefening kun je ook zelf een categorienaam typen; deze verschijnt daarna automatisch in de oefeningenkiezer als filter.

Onder **MyFitness** kun je per trainingsdatum oefeningen vastleggen. Iedere geselecteerde oefening start met twee warming-upsets en twee werksets; per set vul je herhalingen en kilogrammen in en je kunt extra sets toevoegen. Onder **Oefeningen** beheer je de oefeningenbibliotheek. De elf aangeleverde basisoefeningen worden automatisch toegevoegd aan bestaande en nieuwe gebruikersdatabases.

Het eerste tabblad **Overzicht** combineert de geregistreerde voeding, fitness en energiebalans over een zelfgekozen van/tot-datum. Beide datums staan bij het openen standaard op vandaag. De verbranding staat per dag in het overzicht en kan daar direct worden aangepast; de app telt de dagen op en berekent `verbrand - gegeten`. Ook het volledige gecombineerde overzicht kan over een zelfgekozen datumperiode als PDF worden geëxporteerd. MyFitness heeft daarnaast een eigen PDF-export. Onder **Vrienden** zijn de andere geregistreerde gebruikers zichtbaar en kan hun overzicht alleen-lezen worden bekeken.

## Accounts

Iedere gebruiker heeft een eigen, volledig gescheiden productendatabase, maaltijden en MyHealth-dagboek. Het standaardaccount is:

- Gebruikersnaam: `admin`
- Wachtwoord: `test`

Nieuwe gebruikers kunnen zichzelf via **Account aanmaken** registreren.

## Starten op Windows

1. Installeer Python 3.11 of nieuwer vanaf python.org (vink **Add Python to PATH** aan).
2. Pak dit project uit en open een opdrachtprompt in deze map.
3. Voer uit:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

4. Open http://127.0.0.1:5000 in je browser.

## Starten op macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open daarna http://127.0.0.1:5000.

De database wordt bij de eerste start automatisch aangemaakt en gevuld met de 16 opgegeven basisproducten. Verwijder `voeding.db` om helemaal opnieuw te beginnen.

## Render

Gunicorn staat standaard in `requirements.txt`. Gebruik op Render:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

Stel een vaste, willekeurige `SECRET_KEY` in als environment variable. De databases zijn `auth.db`, `voeding.db` (admin) en bestanden in `user_data/`. Koppel op Render een persistent disk aan bijvoorbeeld `/var/data` en voeg `DATA_DIR=/var/data` als environment variable toe als accounts en gegevens na deploys en herstarts bewaard moeten blijven. Zonder persistent disk is het lokale bestandssysteem van Render tijdelijk.
