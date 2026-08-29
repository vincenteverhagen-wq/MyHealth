# MyHealth v19

Een Flask-website voor voeding, fitness en dagelijkse energiebalans.

## Nieuw in v19

- **Productcategorieën en oefeningcategorieën zijn nu volledig gescheiden.** Een categorie die je bij Producten toevoegt, verschijnt niet bij Oefeningen en andersom.
- In zowel **Producten** als **Oefeningen** staat nu een eigen categoriebeheer. Daar kun je categorieën toevoegen, hernoemen en verwijderen. Bij verwijderen worden gekoppelde items naar `Overig` verplaatst.
- De vaste categorie `Overig` kan niet worden verwijderd of hernoemd.
- In **Overzicht** staan de drie kolommen nu als **Voeding → Verbranding → Fitness**.
- De volledige productcatalogus staat ook in `producten.csv`.
- Onder **Producten** kun je een CSV downloaden en een nieuwe CSV uploaden. Nieuwe productnamen worden toegevoegd; bestaande namen worden overgeslagen.
- Onder **Meer → Mijn oefeningen** kun je herbruikbare trainingsschema's maken, bijvoorbeeld `Chestday`. Een schema bewaart oefeningen, warming-upsets, werksets, herhalingen en gewichten.
- In **MyFitness** kun je zo'n schema met één klik inladen voor de gekozen trainingsdatum.
- Iedere gebruiker krijgt een eigen map onder `personen/persoon_<id>/` met:
  - `myhealth.db` — voeding, maaltijden, fitness, verbranding en trainingsschema's;
  - `producten.csv` — de actuele productcatalogus van die persoon;
  - `persoon.json` — herkenbare basisinformatie.
- Bestaande v17/v18-data uit `voeding.db` of `user_data/user_<id>.db` wordt bij de eerste start automatisch naar de nieuwe personenmap gekopieerd.
- Het mobiele **Meer**-menu is aangepast zodat de dropdown niet meer door de horizontale navigatie wordt afgesneden.

## Producten CSV

De standaard `producten.csv` gebruikt puntkomma's en deze kolommen:

```text
naam;categorie;energie;vet;verzadigd_vet;koolhydraten;suikers;vezels;eiwit;zout
```

Komma's als decimaalteken worden ondersteund. Ook Engelse kolomnamen zoals `name` en `category` worden geaccepteerd. De import voegt alleen nieuwe productnamen toe.

## Accounts en opslag

Het standaardaccount is:

- Gebruikersnaam: `admin`
- Wachtwoord: `test`

Bewaar bij een lokale update vooral de map `personen/` en `auth.db`. De map `personen/` staat bewust in `.gitignore`, zodat persoonlijke voortgang niet per ongeluk in een publieke GitHub-repository terechtkomt.

### Render

Op Render is de lokale schijf zonder permanente opslag tijdelijk. Als `personen/` en `auth.db` ook na een redeploy moeten blijven bestaan, laat `DATA_DIR` naar permanente opslag wijzen, bijvoorbeeld `/var/data`.

Gunicorn staat in `requirements.txt`. Gebruik:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

Stel ook een willekeurige `SECRET_KEY` in als environment variable.

## Starten op Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open daarna `http://127.0.0.1:5000`.

## Starten op macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
