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

4. **Skonfiguruj zmienne środowiskowe** (opcjonalnie dla lokalnego developmentu):
```bash
# Skopiuj przykładowy plik konfiguracji
cp env.example .env

# Edytuj .env i ustaw swoje wartości
nano .env
```

5. Otwórz w przeglądarce: `http://localhost:5001`

## Konfiguracja (.env)

Aplikacja używa zmiennych środowiskowych do konfiguracji. Wszystkie ustawienia mają sensowne wartości domyślne, ale **dla produkcji MUSISZ** ustawić własne wartości.

### Generowanie SECRET_KEY

```bash
# Wygeneruj bezpieczny klucz:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Plik .env (produkcja)

Utwórz plik `.env` w głównym katalogu aplikacji:

```env
# REQUIRED: Secret key dla Flask sessions
SECRET_KEY=twoj-wygenerowany-sekretny-klucz-tutaj

# OPTIONAL: Whitelist dozwolonych domen (rozdzielone przecinkiem)
# Pozostaw puste aby zezwolić na wszystkie domeny (nie zalecane dla produkcji)
ALLOWED_DOMAINS=cropink.com,dataoctopus.io,trusted-domain.com

# OPTIONAL: Maksymalny rozmiar pliku XML w bajtach (domyślnie: 10MB)
MAX_XML_SIZE=10485760

# OPTIONAL: Timeout dla żądań HTTP w sekundach (domyślnie: 30)
REQUEST_TIMEOUT=30

# OPTIONAL: Środowisko (development/production)
FLASK_ENV=production

# OPTIONAL: Tryb debug (False dla produkcji)
DEBUG=False

# OPTIONAL: Port aplikacji (domyślnie: 5001)
PORT=5001
```

### Funkcje bezpieczeństwa

Aplikacja zawiera następujące mechanizmy bezpieczeństwa:

1. **Walidacja URL** - blokuje dostęp do:
   - Prywatnych adresów IP (192.168.x.x, 10.x.x.x)
   - Adresów lokalnych (localhost, 127.0.0.1)
   - Nieprawidłowych protokołów (tylko http/https)

2. **XXE Protection** - używa `defusedxml` do ochrony przed XML External Entity attacks

3. **Limit rozmiaru** - sprawdza rozmiar pliku XML przed i podczas pobierania

4. **Domain whitelisting** - opcjonalnie ogranicza dostęp tylko do zaufanych domen

5. **Timeouty** - konfigurowane timeouty dla żądań HTTP

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

# Dezaktywuj środowisko
deactivate
```

### 2. Konfiguracja środowiska

```bash
# Skopiuj przykładowy plik .env
cp env.example .env

# Wygeneruj SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env

# Edytuj .env i dostosuj do swoich potrzeb
nano .env

# WAŻNE: Ustaw właściciela plików na ubuntu
sudo chown -R ubuntu:ubuntu /www/wwwroot/s1.malec.in

# Ustaw odpowiednie uprawnienia
sudo chmod 640 .env  # .env nie powinien być czytelny dla innych
sudo chmod 755 /www/wwwroot/s1.malec.in
```

### 3. Konfiguracja usługi systemd

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

### 4. Podstawowe komendy

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

# Pobierz najnowsze zmiany
git pull origin main

# Aktywuj środowisko wirtualne
source venv/bin/activate

# Zainstaluj/zaktualizuj zależności
pip install -r requirements.txt --upgrade

# Sprawdź czy .env zawiera wszystkie nowe zmienne
# Porównaj z env.example
diff .env env.example || true

# Dezaktywuj środowisko
deactivate

# Restart usługi
sudo systemctl restart feedcompare

# Sprawdź logi
sudo journalctl -u feedcompare -f
```

### Migracja z poprzedniej wersji

Jeśli aktualizujesz z wersji bez pliku `.env`:

```bash
# Zatrzymaj usługę
sudo systemctl stop feedcompare

# Utwórz plik .env
cp env.example .env

# Wygeneruj SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env

# Edytuj .env
nano .env

# Ustaw właściciela
sudo chown ubuntu:ubuntu .env
sudo chmod 640 .env

# Uruchom usługę
sudo systemctl start feedcompare
```

## Autor

Damian Malec

## Licencja

MIT

