import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os
import requests

class XMLFeedComparator:
    def __init__(self, source1, source2):
        self.source1 = source1
        self.source2 = source2
        self.feed1_data = {}
        self.feed2_data = {}

    def _get_xml_content(self, source):
        print(f"Pobieranie danych z: {source}...")
        try:
            if source.startswith('http://') or source.startswith('https://'):
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                print("✓ Pobrano pomyślnie.")
                return response.content
            elif os.path.exists(source):
                with open(source, 'rb') as f:
                    print("✓ Odczytano pomyślnie.")
                    return f.read()
            else:
                print(f"❌ Błąd: Plik lub URL '{source}' nie istnieje lub jest nieprawidłowy.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Błąd sieciowy podczas pobierania {source}: {e}")
            return None
        except Exception as e:
            print(f"❌ Wystąpił nieoczekiwany błąd dla {source}: {e}")
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
            print(f"Błąd podczas parsowania: {str(e)}")
            return {}
    
    def compare_feeds(self):
        print("\n--- Przetwarzanie pierwszego źródła ---")
        content1 = self._get_xml_content(self.source1)
        print("\n--- Przetwarzanie drugiego źródła ---")
        content2 = self._get_xml_content(self.source2)

        if content1 is None or content2 is None:
            print("\nPrzerwano porównanie z powodu błędu wczytywania danych.")
            return None

        print("\nParsowanie pierwszego feeda...")
        self.feed1_data = self.parse_xml_feed(content1)
        print(f"  -> Znaleziono {len(self.feed1_data)} produktów w feedzie 1.")
        
        print("Parsowanie drugiego feeda...")
        self.feed2_data = self.parse_xml_feed(content2)
        print(f"  -> Znaleziono {len(self.feed2_data)} produktów w feedzie 2.")
        
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
        
        return {
            'only_in_feed1': only_in_feed1, 'only_in_feed2': only_in_feed2,
            'differences': products_with_differences, 'total_feed1': len(self.feed1_data),
            'total_feed2': len(self.feed2_data)
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

    def generate_excel_report(self, output_path='porownanie_feedow.xlsx'):
        comparison_results = self.compare_feeds()

        if comparison_results is None or (comparison_results['total_feed1'] == 0 and comparison_results['total_feed2'] == 0):
             print("\nNie wygenerowano raportu, ponieważ nie wczytano żadnych danych produktów.")
             return
        
        print("\nGenerowanie raportu Excel...")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # --- Arkusz 1: Podsumowanie (bez zmian) ---
            summary_data = {
                'Metryka': ['Produkty w Feed 1', 'Produkty w Feed 2', 'Produkty tylko w Feed 1',
                            'Produkty tylko w Feed 2', 'Produkty wspólne', 'Produkty z różnicami'],
                'Wartość': [comparison_results['total_feed1'], comparison_results['total_feed2'],
                            len(comparison_results['only_in_feed1']), len(comparison_results['only_in_feed2']),
                            len(self.feed1_data.keys() & self.feed2_data.keys()),
                            len(set([d['Product ID'] for d in comparison_results['differences']]))]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Podsumowanie', index=False)
            
            # --- Arkusze 2 i 3: Produkty unikalne (bez zmian) ---
            if comparison_results['only_in_feed1']:
                df_only1 = pd.DataFrame({'Product ID': sorted(list(comparison_results['only_in_feed1']))})
                df_only1.to_excel(writer, sheet_name='Tylko w Feed 1', index=False)
            
            if comparison_results['only_in_feed2']:
                df_only2 = pd.DataFrame({'Product ID': sorted(list(comparison_results['only_in_feed2']))})
                df_only2.to_excel(writer, sheet_name='Tylko w Feed 2', index=False)
            
            # --- Arkusz 4: NOWY, CZYTELNY RAPORT RÓŻNIC ---
            if comparison_results['differences']:
                # Tworzymy DataFrame ze wszystkimi różnicami
                df_diff = pd.DataFrame(comparison_results['differences'])
                # Sortujemy dane najpierw po Product ID, a potem po nazwie Pola
                df_diff_sorted = df_diff.sort_values(by=['Product ID', 'Pole']).reset_index(drop=True)
                # Zapisujemy posortowane dane do nowego arkusza
                df_diff_sorted.to_excel(writer, sheet_name='Szczegółowe Różnice', index=False)


        print(f"\n✓ Raport został zapisany: {output_path}")
        print("\nPodsumowanie:")
        print(f"  • Produkty tylko w Feed 1: {len(comparison_results['only_in_feed1'])}")
        print(f"  • Produkty tylko w Feed 2: {len(comparison_results['only_in_feed2'])}")
        print(f"  • Produkty z różnicami: {len(set([d['Product ID'] for d in comparison_results['differences']]))}")
        print(f"  • Łącznie różnic (w polach): {len(comparison_results['differences'])}")

def main():
    print("=" * 60)
    print("PORÓWNYWANIE FEEDÓW PRODUKTOWYCH XML (z pliku lub URL)")
    print("=" * 60)
    
    file1 = input("\nPodaj ścieżkę lub URL do pierwszego pliku XML: ").strip()
    file2 = input("\nPodaj ścieżkę lub URL do drugiego pliku XML: ").strip()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"porownanie_feedow_{timestamp}.xlsx"
    
    comparator = XMLFeedComparator(file1, file2)
    comparator.generate_excel_report(output_file)
    
    print("\n" + "=" * 60)
    print("ZAKOŃCZONO")
    print("=" * 60)

if __name__ == "__main__":
    main()