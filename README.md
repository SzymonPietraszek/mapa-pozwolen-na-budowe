# Opis

To repozytorium zawiera kod do wizualizacji pozwoleń na budowe na mapie.

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
python ./script/process_parcels.py "https://www.bip.krakow.pl/plik.php?zid=715723&wer=0&new=t&mode=shw"
```

Wyjście ze środowiska pythonowego:
```
deactivate
```
