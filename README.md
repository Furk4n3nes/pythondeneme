# Eğitim Video Platformu

Bu proje, eğitim videoları paylaşımı için geliştirilmiş bir web uygulamasıdır.

## Gereksinimler

- Python 3.9.12
- MSSQL Server
- ODBC Driver 17 for SQL Server

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```

2. MSSQL Server'da 'STEAM' adında bir veritabanı oluşturun.

3. app.py dosyasındaki veritabanı bağlantı ayarlarını kendi ortamınıza göre düzenleyin.

## Çalıştırma

```bash
python app.py
```

Uygulama varsayılan olarak http://localhost:5000 adresinde çalışacaktır.

## Önemli Notlar

- Python 3.9.12 sürümü ile test edilmiştir
- MSSQL Server bağlantısı için ODBC Driver 17 gereklidir
- Veritabanı şeması otomatik olarak oluşturulacaktır 