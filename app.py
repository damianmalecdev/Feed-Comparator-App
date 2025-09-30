import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os
import requests
import io

# 1. DODANE: Importujemy 'session'
from flask import Flask, render_template, request, send_file, session

# --- Klasa XMLFeedComparator (bez zmian) ---
class XMLFeedComparator:
    # ... (cała klasa pozostaje identyczna jak wcześniej) ...
    def __init__(self, source1, source2):
        self.source1 = source1
        self.source2 = source2
        self.feed1_data = {}
        self.feed2_data = {}

    def _get_xml_content(self, source):
        try:
            if source.startswith('http://') or source.startswith('https://'):
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                return response.content
            elif os.path.exists(source):
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
    
    def compare_feeds(self):
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
        for product_id in common_products:
            prod1 = self.feed1_data[product_id]
            prod2 = self.feed2_data[product_id]
            differences = self.find_differences(product_id, prod1, prod2)
            if differences:
                products_with_differences.extend(differences)

        sorted_differences = sorted(products_with_differences, key=lambda d: (d['Product ID'], d['Pole']))

        return {
            'only_in_feed1': sorted(list(only_in_feed1)), 
            'only_in_feed2': sorted(list(only_in_feed2)),
            'differences': sorted_differences, 
            'total_feed1': len(self.feed1_data),
            'total_feed2': len(self.feed2_data),
            'common_total': len(common_products),
            'diff_products_total': len(set(d['Product ID'] for d in products_with_differences))
        }
    
    def find_differences(self, product_id, prod1, prod2):
        differences = []
        all_keys = set(prod1.keys()) | set(prod2.keys())
        for key in all_keys:
            val1 = prod1.get(key, '[BRAK]')
            val2 = prod2.get(key, '[BRAK]')
            if val1 != val2:
                differences.append({
                    'Product ID': product_id, 'Pole': key, 'Wartość Feed 1': val1,
                    'Wartość Feed 2': val2
                })
        return differences

    def generate_excel_report(self):
        comparison_results = self.compare_feeds()
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
# 2. DODANE: Klucz do obsługi sesji. Zmień ten tekst na dowolny inny, losowy.
app.secret_key = 'bardzo-tajny-klucz-do-sesji-123'

# 3. ZMIENIONE: Funkcja index odczytuje dane z sesji
@app.route('/')
def index():
    # Używamy session.get(), aby uniknąć błędu przy pierwszym uruchomieniu
    last_feed1 = session.get('last_feed1', '')
    last_feed2 = session.get('last_feed2', '')
    return render_template('index.html', last_feed1=last_feed1, last_feed2=last_feed2)

@app.route('/compare', methods=['POST'])
def compare():
    feed1_url = request.form['feed1']
    feed2_url = request.form['feed2']

    # 3. DODANE: Zapisujemy URL-e w sesji po ich pobraniu z formularza
    session['last_feed1'] = feed1_url
    session['last_feed2'] = feed2_url

    if not feed1_url or not feed2_url:
        return render_template('index.html', error="Proszę podać oba adresy URL.")
    
    comparator = XMLFeedComparator(feed1_url, feed2_url)
    results = comparator.compare_feeds()

    if results is None:
        return render_template('index.html', error="Nie udało się przetworzyć plików. Sprawdź adresy URL i format XML.")

    return render_template(
        'results.html', 
        results=results,
        feed1_url=feed1_url,
        feed2_url=feed2_url
    )

@app.route('/download_excel')
def download_excel():
    feed1_url = request.args.get('feed1')
    feed2_url = request.args.get('feed2')

    if not feed1_url or not feed2_url:
        return "Brak adresów URL do wygenerowania raportu.", 400

    comparator = XMLFeedComparator(feed1_url, feed2_url)
    excel_buffer = comparator.generate_excel_report()

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
    app.run(debug=True, port=5000)