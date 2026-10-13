# Opis

To repozytorium zawiera kod do wizualizacji pozwoleń na budowe na mapie. Skrypt potrzebny do wizualizacji dziala tylko z pozwoleniami na budowę dla Krakowa: https://www.bip.krakow.pl/?dok_id=107889. Dla innych pozwoleń prawdopodobnie trzeba dokonać zmian.

# Jak uzywac

Sklonuj kod lokalnie i wejdź do folderu z repozytorium. Wszystkie komendy będą wykonywane z tej ścieżki.

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
python ./script/process_parcels.py "https://www.bip.krakow.pl/plik.php?zid=715390&wer=0&new=t&mode=shw"
cp ./script/out/parcels.geojson ./public/parcels.geojson
```

Wyjście ze środowiska pythonowego:
```
deactivate
```
