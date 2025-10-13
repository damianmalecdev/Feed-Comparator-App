import defusedxml.ElementTree as ET
import pandas as pd
from datetime import datetime
import os
import requests
import io
from urllib.parse import urlparse
import ipaddress

from flask import Flask, render_template, request, send_file, session
from config import Config

# --- Klasa XMLFeedComparator (bez zmian) ---
class XMLFeedComparator:
    # ... (cała klasa pozostaje identyczna jak wcześniej) ...
    def __init__(self, source1, source2):
        self.source1 = source1
        self.source2 = source2
        self.feed1_data = {}
        self.feed2_data = {}

    def _validate_url(self, url):
        """
        Validates URL to prevent SSRF attacks.
        Returns tuple: (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False, f"Invalid protocol: {parsed.scheme}. Only http/https allowed."
            
            # Check URL length
            if len(url) > 2048:
                return False, "URL too long (max 2048 characters)"
            
            # Check if hostname exists
            if not parsed.hostname:
                return False, "Invalid URL: no hostname found"
            
            # Check against allowed domains if configured
            if Config.ALLOWED_DOMAINS:
                hostname_allowed = False
                for allowed_domain in Config.ALLOWED_DOMAINS:
                    if parsed.hostname == allowed_domain or parsed.hostname.endswith('.' + allowed_domain):
                        hostname_allowed = True
                        break
                
                if not hostname_allowed:
                    return False, f"Domain {parsed.hostname} not in allowed list"
            
            # Block private/local IP addresses
            try:
                # Try to resolve hostname to IP
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False, f"Access to private/local IP addresses is forbidden"
            except ValueError:
                # Hostname is not an IP address, that's fine
                pass
            
            # Block common local hostnames
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if parsed.hostname.lower() in blocked_hosts:
                return False, f"Access to {parsed.hostname} is forbidden"
            
            return True, None
            
        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    def _get_xml_content(self, source):
        try:
            if source.startswith('http://') or source.startswith('https://'):
                # Validate URL first
                is_valid, error_msg = self._validate_url(source)
                if not is_valid:
                    print(f"URL validation failed: {error_msg}")
                    return None
                
                # Fetch XML with configured timeout
                response = requests.get(
                    source, 
                    timeout=Config.REQUEST_TIMEOUT,
                    stream=True  # Stream to check size before loading
                )
                response.raise_for_status()
                
                # Check content size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > Config.MAX_XML_SIZE:
                    print(f"XML file too large: {content_length} bytes (max: {Config.MAX_XML_SIZE})")
                    return None
                
                # Read content with size limit
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > Config.MAX_XML_SIZE:
                        print(f"XML file exceeded size limit during download")
                        return None
                
                return content
            elif os.path.exists(source):
                # Check file size before reading
                file_size = os.path.getsize(source)
                if file_size > Config.MAX_XML_SIZE:
                    print(f"XML file too large: {file_size} bytes (max: {Config.MAX_XML_SIZE})")
                    return None
                    
                with open(source, 'rb') as f:
                    return f.read()
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"Błąd sieciowy: {e}")
            return None
        except Exception as e:
            print(f"Nieoczekiwany błąd: {e}")
            return None

    def parse_xml_feed(self, xml_content):
        try:
            root = ET.fromstring(xml_content)
            products = {}
            for item in root.iter():
                item_tag = item.tag.split('}', 1)[-1]
                if item_tag.lower() in ['item', 'product', 'entry', 'offer']:
                    product_data = {}
                    product_id = None
                    for child in item:
                        child_tag = child.tag.split('}', 1)[-1]
                        value = child.text.strip() if child.text else ''
                        if child_tag.lower() in ['id', 'product_id', 'sku', 'g:id']:
                            product_id = value
                        product_data[child_tag] = value
                    if product_id:
                        products[product_id] = product_data
            return products
        except Exception as e:
            print(f"Błąd parsowania: {str(e)}")
            return {}
    
    def get_all_attributes(self):
        """Pobiera wszystkie unikalne atrybuty z pierwszego produktu każdego feeda"""
        content1 = self._get_xml_content(self.source1)
        content2 = self._get_xml_content(self.source2)

        if content1 is None or content2 is None:
            return None, None

        self.feed1_data = self.parse_xml_feed(content1)
        self.feed2_data = self.parse_xml_feed(content2)
        
        all_attributes = set()
        
        # Pobierz atrybuty z pierwszego produktu z feed1
        if self.feed1_data:
            first_product = list(self.feed1_data.values())[0]
            all_attributes.update(first_product.keys())
        
        # Pobierz atrybuty z pierwszego produktu z feed2
        if self.feed2_data:
            first_product = list(self.feed2_data.values())[0]
            all_attributes.update(first_product.keys())
        
        return sorted(list(all_attributes)), {
            'total_feed1': len(self.feed1_data),
            'total_feed2': len(self.feed2_data)
        }
    
    def compare_feeds(self, excluded_attributes=None):
        if excluded_attributes is None:
            excluded_attributes = []
            
        content1 = self._get_xml_content(self.source1)
        content2 = self._get_xml_content(self.source2)

        if content1 is None or content2 is None:
            return None

        self.feed1_data = self.parse_xml_feed(content1)
        self.feed2_data = self.parse_xml_feed(content2)
        
        only_in_feed1 = set(self.feed1_data.keys()) - set(self.feed2_data.keys())
        only_in_feed2 = set(self.feed2_data.keys()) - set(self.feed1_data.keys())
        common_products = set(self.feed1_data.keys()) & set(self.feed2_data.keys())
        
        products_with_differences = []
        attribute_diff_count = {}  # Licznik różnic per atrybut
        
        for product_id in common_products:
            prod1 = self.feed1_data[product_id]
            prod2 = self.feed2_data[product_id]
            differences = self.find_differences(product_id, prod1, prod2, excluded_attributes)
            if differences:
                products_with_differences.extend(differences)
                # Zlicz różnice per atrybut
                for diff in differences:
                    attr_name = diff['Pole']
                    attribute_diff_count[attr_name] = attribute_diff_count.get(attr_name, 0) + 1

        sorted_differences = sorted(products_with_differences, key=lambda d: (d['Product ID'], d['Pole']))
        
        # Sortuj statystyki atrybutów według liczby różnic (malejąco)
        attribute_stats = sorted(
            [{'attribute': k, 'count': v} for k, v in attribute_diff_count.items()],
            key=lambda x: x['count'],
            reverse=True
        )

        return {
            'only_in_feed1': sorted(list(only_in_feed1)), 
            'only_in_feed2': sorted(list(only_in_feed2)),
            'differences': sorted_differences, 
            'total_feed1': len(self.feed1_data),
            'total_feed2': len(self.feed2_data),
            'common_total': len(common_products),
            'diff_products_total': len(set(d['Product ID'] for d in products_with_differences)),
            'attribute_stats': attribute_stats  # Dodane: statystyki per atrybut
        }
    
    def find_differences(self, product_id, prod1, prod2, excluded_attributes=None):
        if excluded_attributes is None:
            excluded_attributes = []
            
        differences = []
        all_keys = set(prod1.keys()) | set(prod2.keys())
        excluded_count = 0
        
        for key in all_keys:
            # Pomiń wykluczone atrybuty
            if key in excluded_attributes:
                excluded_count += 1
                continue
                
            val1 = prod1.get(key, '[BRAK]')
            val2 = prod2.get(key, '[BRAK]')
            if val1 != val2:
                differences.append({
                    'Product ID': product_id, 'Pole': key, 'Wartość Feed 1': val1,
                    'Wartość Feed 2': val2
                })
        
        if excluded_count > 0 and len(differences) > 0:
            print(f"   Produkt {product_id}: znaleziono {len(differences)} różnic (pominięto {excluded_count} atrybutów)")
        
        return differences

    def generate_excel_report(self, excluded_attributes=None):
        comparison_results = self.compare_feeds(excluded_attributes)
        if comparison_results is None:
            return None

        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            summary_data = {
                'Metryka': ['Produkty w Feed 1', 'Produkty w Feed 2', 'Produkty tylko w Feed 1', 'Produkty tylko w Feed 2', 'Produkty wspólne', 'Produkty z różnicami'],
                'Wartość': [
                    comparison_results['total_feed1'], 
                    comparison_results['total_feed2'], 
                    len(comparison_results['only_in_feed1']), 
                    len(comparison_results['only_in_feed2']), 
                    comparison_results['common_total'],
                    comparison_results['diff_products_total']
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Podsumowanie', index=False)
            
            # Dodaj statystyki różnic per atrybut
            if comparison_results.get('attribute_stats'):
                attr_stats_data = []
                for stat in comparison_results['attribute_stats']:
                    percentage = (stat['count'] / comparison_results['common_total'] * 100) if comparison_results['common_total'] > 0 else 0
                    attr_stats_data.append({
                        'Atrybut': stat['attribute'],
                        'Liczba różnic': stat['count'],
                        'Procent produktów (%)': round(percentage, 1)
                    })
                df_attr_stats = pd.DataFrame(attr_stats_data)
                df_attr_stats.to_excel(writer, sheet_name='Statystyki atrybutów', index=False)
            
            if comparison_results['only_in_feed1']:
                pd.DataFrame({'Product ID': comparison_results['only_in_feed1']}).to_excel(writer, sheet_name='Tylko w Feed 1', index=False)
            if comparison_results['only_in_feed2']:
                pd.DataFrame({'Product ID': comparison_results['only_in_feed2']}).to_excel(writer, sheet_name='Tylko w Feed 2', index=False)
            
            if comparison_results['differences']:
                df_diff = pd.DataFrame(comparison_results['differences'])
                df_diff.to_excel(writer, sheet_name='Szczegółowe Różnice', index=False)

        output_buffer.seek(0)
        return output_buffer


# --- Aplikacja Flask ---
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Validate configuration and show warnings
config_warnings = Config.validate()
for warning in config_warnings:
    print(f"⚠️  {warning}")

# 3. ZMIENIONE: Funkcja index odczytuje dane z sesji
@app.route('/')
def index():
    # Używamy session.get(), aby uniknąć błędu przy pierwszym uruchomieniu
    last_feed1 = session.get('last_feed1', '')
    last_feed2 = session.get('last_feed2', '')
    return render_template('index.html', last_feed1=last_feed1, last_feed2=last_feed2)

@app.route('/analyze', methods=['POST'])
def analyze():
    feed1_url = request.form['feed1']
    feed2_url = request.form['feed2']

    # Zapisujemy URL-e w sesji
    session['last_feed1'] = feed1_url
    session['last_feed2'] = feed2_url

    if not feed1_url or not feed2_url:
        return render_template('index.html', error="Proszę podać oba adresy URL.")
    
    comparator = XMLFeedComparator(feed1_url, feed2_url)
    attributes, feed_info = comparator.get_all_attributes()

    if attributes is None or feed_info is None:
        return render_template('index.html', error="Nie udało się przetworzyć plików. Sprawdź adresy URL i format XML.")

    return render_template(
        'select_attributes.html',
        attributes=attributes,
        feed_info=feed_info,
        feed1_url=feed1_url,
        feed2_url=feed2_url
    )

@app.route('/compare', methods=['POST'])
def compare():
    feed1_url = request.form['feed1']
    feed2_url = request.form['feed2']
    
    # Pobierz wykluczone atrybuty z formularza (checkboxy)
    excluded_attributes = request.form.getlist('excluded_attributes')
    
    print(f"🔍 Rozpoczynam porównanie:")
    print(f"   Feed 1: {feed1_url}")
    print(f"   Feed 2: {feed2_url}")
    print(f"   Wykluczone atrybuty ({len(excluded_attributes)}): {excluded_attributes}")

    # Zapisujemy URL-e w sesji po ich pobraniu z formularza
    session['last_feed1'] = feed1_url
    session['last_feed2'] = feed2_url
    session['excluded_attributes'] = excluded_attributes

    if not feed1_url or not feed2_url:
        return render_template('index.html', error="Proszę podać oba adresy URL.")
    
    comparator = XMLFeedComparator(feed1_url, feed2_url)
    results = comparator.compare_feeds(excluded_attributes)

    if results is None:
        print("❌ Błąd: results jest None!")
        return render_template('index.html', error="Nie udało się przetworzyć plików. Sprawdź adresy URL i format XML.")

    print(f"✅ Porównanie zakończone:")
    print(f"   Produkty z różnicami: {results['diff_products_total']}")
    print(f"   Liczba różnic: {len(results['differences'])}")

    return render_template(
        'results.html', 
        results=results,
        feed1_url=feed1_url,
        feed2_url=feed2_url,
        excluded_attributes=excluded_attributes
    )

@app.route('/download_excel')
def download_excel():
    feed1_url = request.args.get('feed1')
    feed2_url = request.args.get('feed2')
    
    # Pobierz wykluczone atrybuty z sesji
    excluded_attributes = session.get('excluded_attributes', [])

    if not feed1_url or not feed2_url:
        return "Brak adresów URL do wygenerowania raportu.", 400

    comparator = XMLFeedComparator(feed1_url, feed2_url)
    excel_buffer = comparator.generate_excel_report(excluded_attributes)

    if excel_buffer is None:
        return "Błąd podczas generowania pliku Excel.", 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"porownanie_feedow_{timestamp}.xlsx"

    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == "__main__":
    print(f"🚀 Starting Feed Comparator on port {Config.PORT}")
    print(f"   Environment: {Config.FLASK_ENV}")
    print(f"   Debug mode: {Config.DEBUG}")
    if Config.ALLOWED_DOMAINS:
        print(f"   Allowed domains: {', '.join(Config.ALLOWED_DOMAINS)}")
    else:
        print(f"   Allowed domains: ALL (not recommended for production)")
    app.run(debug=Config.DEBUG, port=Config.PORT)