# Feed Comparator App

Aplikacja w Pythonie (Flask) do porównywania feedów produktowych XML.

## Funkcje

- 📊 Porównywanie dwóch feedów XML (z URL lub plików lokalnych)
- 🔍 Identyfikacja produktów unikalnych dla każdego feedu
- ⚙️ Wybór atrybutów do wykluczenia z analizy
- 📈 Statystyki różnic per atrybut z procentami
- 📑 Generowanie szczegółowych raportów Excel
- 💾 Zapamiętywanie ostatnio używanych URL-i

## Wymagania

- Python 3.9+
- Flask
- pandas
- openpyxl
- requests
- gunicorn (dla produkcji)

## Instalacja lokalna

1. Sklonuj repozytorium:
```bash
git clone https://github.com/damianmalecdev/Feed-Comparator-App.git
cd Feed-Comparator-App
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

3. Uruchom aplikację:
```bash
python3 app.py
```

4. Otwórz w przeglądarce: `http://localhost:5001`

## Instalacja na serwerze (systemd)

### 1. Przygotowanie środowiska

```bash
# Utwórz katalog aplikacji
mkdir -p /www/wwwroot/s1.malec.in
cd /www/wwwroot/s1.malec.in

# Sklonuj repozytorium
git clone https://github.com/damianmalecdev/Feed-Comparator-App.git .

# Utwórz wirtualne środowisko
python3 -m venv venv

# Aktywuj środowisko
source venv/bin/activate

# Zainstaluj zależności
pip install -r requirements.txt
```

### 2. Konfiguracja usługi systemd

```bash
# Skopiuj plik usługi
sudo cp feedcompare.service /etc/systemd/system/

# Przeładuj daemona systemd
sudo systemctl daemon-reload

# Uruchom usługę
sudo systemctl start feedcompare

# Włącz autostart
sudo systemctl enable feedcompare

# Sprawdź status
sudo systemctl status feedcompare
```

### 3. Podstawowe komendy

```bash
# Start usługi
sudo systemctl start feedcompare

# Stop usługi
sudo systemctl stop feedcompare

# Restart usługi
sudo systemctl restart feedcompare

# Status usługi
sudo systemctl status feedcompare

# Logi
sudo journalctl -u feedcompare -f
```

## Konfiguracja usługi

Plik `feedcompare.service` zawiera następującą konfigurację:

- **Port**: 8010
- **Workers**: 3 (gunicorn workers)
- **Restart**: automatyczny restart przy awarii
- **RestartSec**: 5 sekund opóźnienia przed restartem
- **TimeoutStopSec**: 20 sekund na graceful shutdown

### Dostosowanie konfiguracji

Jeśli potrzebujesz zmienić port lub liczbę workerów, edytuj plik:

```bash
sudo nano /etc/systemd/system/feedcompare.service
```

Zmień linię `ExecStart`:
```
ExecStart=/www/wwwroot/s1.malec.in/venv/bin/python3 -m gunicorn --workers 3 --bind 0.0.0.0:8010 app:app
```

Po zmianach:
```bash
sudo systemctl daemon-reload
sudo systemctl restart feedcompare
```

## Nginx (opcjonalnie)

Przykładowa konfiguracja Nginx jako reverse proxy:

```nginx
server {
    listen 80;
    server_name s1.malec.in;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Struktura projektu

```
.
├── app.py                      # Główna aplikacja Flask
├── requirements.txt            # Zależności Python
├── Procfile                    # Konfiguracja dla Heroku
├── feedcompare.service         # Plik usługi systemd
├── README.md                   # Ta dokumentacja
└── templates/
    ├── index.html              # Strona główna
    ├── select_attributes.html  # Wybór atrybutów do wykluczenia
    └── results.html            # Strona z wynikami
```

## Użytkowanie

1. Wprowadź URL-e dwóch feedów XML
2. Kliknij "Analizuj pliki"
3. Wybierz atrybuty do wykluczenia (lub pomiń ten krok)
4. Kliknij "Porównaj z wybranymi wykluczeniami"
5. Zobacz wyniki:
   - Podsumowanie różnic
   - Statystyki różnic per atrybut
   - Szczegółową tabelę różnic
6. Pobierz raport Excel dla dalszej analizy

## Aktualizacja aplikacji

```bash
cd /www/wwwroot/s1.malec.in
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart feedcompare
```

## Autor

Damian Malec

## Licencja

MIT

