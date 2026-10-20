# Opis

To repozytorium zawiera kod do wizualizacji pozwoleń na budowe na mapie. Skrypt potrzebny do wizualizacji działa tylko z pozwoleniami na budowę dla Krakowa: https://www.bip.krakow.pl/?dok_id=107889. Dla innych pozwoleń prawdopodobnie trzeba dokonać zmian.

# Jak używac

Sklonuj kod lokalnie i wejdź do folderu z repozytorium. Wszystkie komendy będą wykonywane z tej ścieżki.

## Generowanie geojson działek na podstawie PDF'a

Inicjalizacja środowiska pythonowego (jednorazowa):
```
python3.14 -m venv ./script/.venv
source ./script/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r ./script/requirements.txt
```

Wykonywanie skryptu do przetworzenia danych o pozwoleniach na budowe:
```
source ./script/.venv/bin/activate
python ./script/process_parcels.py
```

Wyjście ze środowiska pythonowego:
```
deactivate
```

## Wizualizacja mapy z działkami

```
npm install
npm run dev
```

W przeglądarce otwórz: http://localhost:5173/

