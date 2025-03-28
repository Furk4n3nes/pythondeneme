from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
import urllib.parse
import re
from markupsafe import Markup
from sqlalchemy import case
from datetime import datetime
import typing
from flask_caching import Cache

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli_anahtar_buraya'
connection_str = 'DRIVER={SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=STEAM;Trusted_Connection=yes;'
app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(connection_str)}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Statik dosyaların önbelleklenmesini engelle
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Cache yapılandırması
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

# SQLAlchemy performans optimizasyonları
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30
app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800

db = SQLAlchemy(app)

@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return text
    return Markup(text.replace('\n', '<br>'))

# Jinja2 filtresi olarak tanımla
@app.template_filter('get_embed_url')
def get_embed_url(url):
    if not url:
        return ''
    
    # YouTube video ID'sini çıkar
    youtube_regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(youtube_regex, url)
    
    if match:
        video_id = match.group(1)
        return f'https://www.youtube.com/embed/{video_id}'
    
    return url

# Kullanıcı oturum kontrolü için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ana sayfa
@app.route('/')
def index():
    # Tüm sınıfları ve videoları çek
    siniflar = db.session.query(Sinif).all()
    
    # Son eklenen videoları çek
    son_videolar = db.session.query(Video).order_by(Video.YuklemeTarihi.desc()).limit(3).all()
    
    # Her video için yükleyen bilgilerini çek
    for video in son_videolar:
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        
        video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
    
    # En çok beğenilen videoları çek
    populer_videolar = db.session.query(Video, db.func.count(Begenme.BegenmeID).label('begeni_sayisi'))\
        .join(Begenme, Video.VideoID == Begenme.VideoID)\
        .group_by(Video)\
        .order_by(db.text('begeni_sayisi DESC'))\
        .limit(3)\
        .all()
    
    # En çok izlenen videoları çek
    cok_izlenen_videolar = db.session.query(Video, db.func.count(Izlenme.IzlenmeID).label('izlenme_sayisi'))\
        .join(Izlenme, Video.VideoID == Izlenme.VideoID)\
        .group_by(Video)\
        .order_by(db.text('izlenme_sayisi DESC'))\
        .limit(3)\
        .all()
    
    # Her video için embed URL ve yükleyen bilgilerini oluştur
    for video in son_videolar:
        video.embed_url = get_embed_url(video.VideoURL)
    
    for video, begeni_sayisi in populer_videolar:
        video.embed_url = get_embed_url(video.VideoURL)
        video.begeni_sayisi = begeni_sayisi
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
    
    for video, izlenme_sayisi in cok_izlenen_videolar:
        video.embed_url = get_embed_url(video.VideoURL)
        video.izlenme_sayisi = izlenme_sayisi
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
    
    return render_template('index.html', 
                         siniflar=siniflar, 
                         son_videolar=son_videolar,
                         populer_videolar=populer_videolar,
                         cok_izlenen_videolar=cok_izlenen_videolar)

# Giriş sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'register':
            try:
                kullanici_tipi = request.form.get('kullanici_tipi')
                kullanici_adi = request.form.get('kullanici_adi')
                email = request.form.get('email')
                sifre = request.form.get('sifre')  # Hash'leme kaldırıldı
                ad = request.form.get('ad')
                soyad = request.form.get('soyad')
                
                # Yeni kullanıcı oluştur
                if kullanici_tipi == 'ogretmen':
                    brans = request.form.get('brans')
                    yeni_kullanici = Ogretmen(
                        KullaniciAdi=kullanici_adi,
                        Email=email,
                        Sifre=sifre,  # Direkt şifreyi kaydet
                        Ad=ad,
                        Soyad=soyad,
                        Brans=brans,
                        KayitTarihi=datetime.now(),
                        AktifMi=True
                    )
                else:
                    yeni_kullanici = Ogrenci(
                        KullaniciAdi=kullanici_adi,
                        Email=email,
                        Sifre=sifre,  # Direkt şifreyi kaydet
                        Ad=ad,
                        Soyad=soyad,
                        KayitTarihi=datetime.now(),
                        AktifMi=True
                    )
                
                db.session.add(yeni_kullanici)
                db.session.commit()
                flash('Kayıt işlemi başarıyla tamamlandı! Giriş yapabilirsiniz.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Kayıt hatası: {str(e)}")
                flash('Kayıt işlemi sırasında bir hata oluştu!', 'danger')
                return redirect(url_for('login', _anchor='register'))
        
        elif form_type == 'login':
            kullanici_tipi = request.form.get('kullanici_tipi')
            email = request.form.get('email')
            sifre = request.form.get('sifre')
            
            if kullanici_tipi == 'ogretmen':
                kullanici = Ogretmen.query.filter_by(Email=email, Sifre=sifre).first()
            elif kullanici_tipi == 'ogrenci':
                kullanici = Ogrenci.query.filter_by(Email=email, Sifre=sifre).first()
            else:
                kullanici = Admin.query.filter_by(Email=email, Sifre=sifre).first()
            
            if kullanici:
                session['user_id'] = kullanici.OgretmenID if kullanici_tipi == 'ogretmen' else (kullanici.OgrenciID if kullanici_tipi == 'ogrenci' else kullanici.AdminID)
                session['user_type'] = 'Ogretmen' if kullanici_tipi == 'ogretmen' else ('Ogrenci' if kullanici_tipi == 'ogrenci' else 'Admin')  # Büyük harfle başlayan versiyonları
                session['user_name'] = f"{kullanici.Ad} {kullanici.Soyad}"
                
                flash('Başarıyla giriş yaptınız!', 'success')
                
                if kullanici_tipi == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif kullanici_tipi == 'ogretmen':
                    return redirect(url_for('ogretmen_dashboard'))
                else:
                    return redirect(url_for('ogrenci_dashboard'))
            else:
                flash('Geçersiz e-posta veya şifre!', 'danger')
                return redirect(url_for('login'))

    return render_template('login.html')

# Çıkış
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Arama fonksiyonu daha sonra implement edilecek
    return render_template('search.html', query=query)

@app.route('/iletisim')
def iletisim():
    return render_template('iletisim.html')

@app.route('/kuramsal-bilgi')
def kuramsal_bilgi():
    return render_template('kuramsal_bilgi.html')

@app.route('/profil')
@login_required
def profil():
    if session['user_type'] == 'Ogretmen':
        return redirect(url_for('ogretmen_profil'))
    elif session['user_type'] == 'Ogrenci':
        return redirect(url_for('ogrenci_profil'))
    else:
        flash('Geçersiz kullanıcı tipi!', 'error')
        return redirect(url_for('login'))

@app.route('/videolarim')
@login_required
def videolarim():
    return render_template('videolarim.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/sinif/<int:sinif_id>')
def sinif_detay(sinif_id):
    sinif = db.session.query(Sinif).get(sinif_id)
    if sinif is None:
        flash('Sınıf bulunamadı', 'error')
        return redirect(url_for('index'))
    return render_template('sinif_detay.html', sinif=sinif)

@app.route('/ders/<int:ders_id>')
@app.route('/ders/<int:ders_id>/video/<int:video_id>')
def ders_detay(ders_id, video_id=None):
    # Dersi çek
    ders = db.session.query(Ders).get(ders_id)
    if not ders:
        flash('Ders bulunamadı', 'error')
        return redirect(url_for('index'))
    
    # Üniteleri çek
    uniteler = db.session.query(Unite)\
        .filter(Unite.DersID == ders_id)\
        .order_by(Unite.UniteNo)\
        .all()
    
    # Her ünite için konuları ve video sayılarını çek
    for unite in uniteler:
        unite.konular = db.session.query(Konu)\
            .filter(Konu.UniteID == unite.UniteID)\
            .order_by(Konu.KonuNo)\
            .all()
        
        for konu in unite.konular:
            konu.video_sayisi = db.session.query(Video)\
                .filter(Video.KonuID == konu.KonuID)\
                .count()
    
    # Eğer video_id varsa, ilgili videoyu ve konuyu bul
    if video_id:
        video = db.session.query(Video).get(video_id)
        if video:
            # Video bilgilerini hazırla
            video.embed_url = get_embed_url(video.VideoURL)
            if video.YukleyenTip == 'Admin':
                yukleyen = db.session.query(Admin).get(video.YukleyenID)
            elif video.YukleyenTip == 'Ogretmen':
                yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
            elif video.YukleyenTip == 'Ogrenci':
                yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
            video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
            
            # Video verilerini JSON formatında hazırla
            video_data = {
                'video_id': video.VideoID,
                'baslik': video.Baslik,
                'aciklama': video.Aciklama,
                'embed_url': video.embed_url,
                'yukleyen_tip': video.YukleyenTip,
                'yukleyen_adi': video.yukleyen_adi,
                'yukleme_tarihi': video.YuklemeTarihi.strftime('%d.%m.%Y %H:%M')
            }
            
            return render_template('ders_detay.html', 
                                ders=ders, 
                                uniteler=uniteler,
                                initial_video=video_data,
                                initial_konu_id=video.KonuID)
    
    return render_template('ders_detay.html', 
                         ders=ders, 
                         uniteler=uniteler)

@app.route('/video/<int:video_id>')
def video_detay(video_id):
    video = db.session.query(Video).get(video_id)
    if video is None:
        flash('Video bulunamadı', 'error')
        return redirect(url_for('index'))
    
    # Video için embed URL oluştur
    video.embed_url = get_embed_url(video.VideoURL)
    return render_template('video_detay.html', video=video)

@app.route('/arama')
def arama():
    # Arama terimini al
    q = request.args.get('q', '').strip()
    
    if not q:
        flash('Lütfen bir arama terimi girin', 'warning')
        return redirect(url_for('index'))
    
    # Unite ve Konu tablolarında arama yap
    arama_sonuclari = db.session.query(Video, Unite, Konu)\
        .join(Konu, Video.KonuID == Konu.KonuID)\
        .join(Unite, Konu.UniteID == Unite.UniteID)\
        .filter(
            db.or_(
                Unite.UniteAdi.ilike(f'%{q}%'),
                Konu.KonuAdi.ilike(f'%{q}%')
            )
        ).all()
    
    # Her video için yükleyen bilgilerini ve embed URL'sini ekle
    videolar = []
    for video, unite, konu in arama_sonuclari:
        # Embed URL'sini oluştur
        video.embed_url = get_embed_url(video.VideoURL)
        
        # Yükleyen bilgilerini al
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        
        video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
        
        # Video nesnesine unite ve konu bilgilerini ekle
        video.unite = unite
        video.konu = konu
        
        videolar.append(video)
    
    return render_template('arama_sonuclari.html', 
                         videolar=videolar, 
                         aranan=q, 
                         sonuc_sayisi=len(videolar))

@app.route('/konu/<int:konu_id>/videolar')
def konu_videolar(konu_id):
    # Konuyu ve videolarını çek
    konu = db.session.query(Konu).get(konu_id)
    if not konu:
        flash('Konu bulunamadı', 'error')
        return redirect(url_for('index'))
    
    # Konunun videolarını çek
    videolar = db.session.query(Video)\
        .filter(Video.KonuID == konu_id)\
        .order_by(Video.YuklemeTarihi.desc())\
        .all()
    
    # Her video için yükleyen bilgilerini ve embed URL'sini ekle
    for video in videolar:
        video.embed_url = get_embed_url(video.VideoURL)
        
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        
        video.yukleyen_adi = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
    
    # Konunun ait olduğu ünite ve ders bilgilerini çek
    unite = konu.unite
    ders = unite.ders
    
    # Dersin tüm ünitelerini sıralı şekilde çek
    ders.uniteler = db.session.query(Unite)\
        .filter(Unite.DersID == ders.DersID)\
        .order_by(Unite.UniteNo)\
        .all()
    
    # Her ünite için konuları çek
    for unite_item in ders.uniteler:
        unite_item.konular = db.session.query(Konu)\
            .filter(Konu.UniteID == unite_item.UniteID)\
            .order_by(Konu.KonuNo)\
            .all()
    
    return render_template('konu_videolar.html', 
                         konu=konu,
                         unite=unite,
                         ders=ders,
                         videolar=videolar)

@app.route('/konu/<int:konu_id>/videolar/json')
def konu_videolar_json(konu_id):
    # Konunun videolarını çek
    videolar = db.session.query(Video)\
        .filter(Video.KonuID == konu_id)\
        .order_by(Video.YuklemeTarihi.desc())\
        .all()
    
    # Her video için yükleyen bilgilerini ve embed URL'sini ekle
    video_list = []
    for video in videolar:
        video_data = {
            'video_id': video.VideoID,
            'baslik': video.Baslik,
            'aciklama': video.Aciklama,
            'embed_url': get_embed_url(video.VideoURL),
            'yukleme_tarihi': video.YuklemeTarihi.strftime('%d.%m.%Y'),
            'yukleyen_tip': video.YukleyenTip
        }
        
        # Yükleyen bilgilerini al
        if video.YukleyenTip == 'Admin':
            yukleyen = db.session.query(Admin).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogretmen':
            yukleyen = db.session.query(Ogretmen).get(video.YukleyenID)
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = db.session.query(Ogrenci).get(video.YukleyenID)
        
        video_data['yukleyen_adi'] = f"{yukleyen.Ad} {yukleyen.Soyad}" if yukleyen else "Bilinmeyen"
        video_list.append(video_data)
    
    return jsonify(video_list)

@app.route('/video/<int:video_id>/yorumlar/json')
def video_yorumlar_json(video_id):
    # Video yorumlarını çek
    yorumlar = db.session.query(Yorum)\
        .filter(Yorum.VideoID == video_id)\
        .order_by(Yorum.YorumTarihi.desc())\
        .all()
    
    # Yorumları JSON formatına dönüştür
    yorum_list = []
    for yorum in yorumlar:
        # Yorum yapan kullanıcı bilgilerini al
        if yorum.YorumYapanTip == 'Admin':
            kullanici = db.session.query(Admin).get(yorum.YorumYapanID)
        elif yorum.YorumYapanTip == 'Ogretmen':
            kullanici = db.session.query(Ogretmen).get(yorum.YorumYapanID)
        elif yorum.YorumYapanTip == 'Ogrenci':
            kullanici = db.session.query(Ogrenci).get(yorum.YorumYapanID)
        
        yorum_data = {
            'yorum_metni': yorum.YorumMetni,
            'yorum_tarihi': yorum.YorumTarihi.strftime('%d.%m.%Y %H:%M'),
            'kullanici_tipi': yorum.YorumYapanTip,
            'kullanici_adi': f"{kullanici.Ad} {kullanici.Soyad}" if kullanici else "Bilinmeyen"
        }
        yorum_list.append(yorum_data)
    
    return jsonify(yorum_list)

@app.route('/mesaj_gonder', methods=['POST'])
@login_required
def mesaj_gonder():
    konu = request.form.get('konu')
    mesaj_metni = request.form.get('mesaj')
    
    # Yeni mesaj oluştur
    yeni_mesaj = Mesaj(
        GonderenTip=session['user_type'],
        GonderenID=session['user_id'],
        AliciTip='Admin',  # Mesajlar varsayılan olarak admin'e gider
        AliciID=1,  # Varsayılan admin ID'si
        MesajIcerik=f"Konu: {konu}\n\n{mesaj_metni}"
    )
    
    try:
        db.session.add(yeni_mesaj)
        db.session.commit()
        flash('Mesajınız başarıyla gönderildi.', 'success')
    except:
        db.session.rollback()
        flash('Mesaj gönderilirken bir hata oluştu.', 'error')
    
    return redirect(url_for('iletisim'))

# Dashboard route'ları
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session['user_type'] != 'Admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    # İstatistikleri hesapla
    toplam_ogretmen = Ogretmen.query.count()
    toplam_ogrenci = Ogrenci.query.count()
    toplam_video = Video.query.count()
    toplam_izlenme = db.session.query(db.func.count(Izlenme.IzlenmeID)).scalar() or 0
    
    # Onay bekleyen videoları çek (ReddetmeSebebi NULL olanlar)
    onay_bekleyen_videolar = db.session.query(
        Video, Ogretmen, Ogrenci, Admin, Konu, Unite, Sinif, Ders
    ).outerjoin(
        Ogretmen, db.and_(Video.YukleyenTip == 'Ogretmen', Video.YukleyenID == Ogretmen.OgretmenID)
    ).outerjoin(
        Ogrenci, db.and_(Video.YukleyenTip == 'Ogrenci', Video.YukleyenID == Ogrenci.OgrenciID)
    ).outerjoin(
        Admin, db.and_(Video.YukleyenTip == 'Admin', Video.YukleyenID == Admin.AdminID)
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).join(
        Sinif, Ders.SinifID == Sinif.SinifID
    ).filter(
        Video.AktifMi == False,
        Video.ReddetmeSebebi == None  # ReddetmeSebebi NULL olanlar
    ).order_by(
        Video.YuklemeTarihi.desc()
    ).all()
    
    # Reddedilen videoları çek (ReddetmeSebebi NULL olmayanlar)
    reddedilen_videolar = db.session.query(
        Video, Ogretmen, Ogrenci, Admin, Konu, Unite, Sinif, Ders
    ).outerjoin(
        Ogretmen, db.and_(Video.YukleyenTip == 'Ogretmen', Video.YukleyenID == Ogretmen.OgretmenID)
    ).outerjoin(
        Ogrenci, db.and_(Video.YukleyenTip == 'Ogrenci', Video.YukleyenID == Ogrenci.OgrenciID)
    ).outerjoin(
        Admin, db.and_(Video.YukleyenTip == 'Admin', Video.YukleyenID == Admin.AdminID)
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).join(
        Sinif, Ders.SinifID == Sinif.SinifID
    ).filter(
        Video.ReddetmeSebebi != None  # ReddetmeSebebi NULL olmayan videolar
    ).order_by(
        Video.YuklemeTarihi.desc()
    ).all()
    
    # Tüm sınıfları çek
    siniflar = Sinif.query.all()
    
    # Her sınıf için öğrenci ve ders sayılarını hesapla
    for sinif in siniflar:
        sinif.ogrenci_sayisi = Ogrenci.query.filter_by(SinifID=sinif.SinifID).count()
        sinif.ders_sayisi = Ders.query.filter_by(SinifID=sinif.SinifID).count()
    
    # Tüm videoları çek
    videolar = db.session.query(
        Video, Ogretmen, Ogrenci, Admin, Konu, Unite, Sinif, Ders
    ).outerjoin(
        Ogretmen, db.and_(Video.YukleyenTip == 'Ogretmen', Video.YukleyenID == Ogretmen.OgretmenID)
    ).outerjoin(
        Ogrenci, db.and_(Video.YukleyenTip == 'Ogrenci', Video.YukleyenID == Ogrenci.OgrenciID)
    ).outerjoin(
        Admin, db.and_(Video.YukleyenTip == 'Admin', Video.YukleyenID == Admin.AdminID)
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).join(
        Sinif, Ders.SinifID == Sinif.SinifID
    ).order_by(
        Video.YuklemeTarihi.desc()
    ).all()
    
    return render_template('admin/dashboard.html',
                         toplam_ogretmen=toplam_ogretmen,
                         toplam_ogrenci=toplam_ogrenci,
                         toplam_video=toplam_video,
                         toplam_izlenme=toplam_izlenme,
                         siniflar=siniflar,
                         videolar=videolar,
                         onay_bekleyen_videolar=onay_bekleyen_videolar,
                         reddedilen_videolar=reddedilen_videolar,
                         get_embed_url=get_embed_url)

@app.route('/ogretmen/dashboard')
@login_required
def ogretmen_dashboard():
    if session.get('user_type') != 'Ogretmen':  # Büyük harfle başlayan versiyonu kontrol et
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('login'))
    
    # İstatistikleri hesapla
    video_sayisi = Video.query.filter_by(
        YukleyenTip='Ogretmen',
        YukleyenID=session['user_id']
    ).count()
    
    izlenme_sayisi = db.session.query(db.func.count(Izlenme.IzlenmeID)).join(Video).filter(
        Video.YukleyenTip=='Ogretmen',
        Video.YukleyenID==session['user_id']
    ).scalar() or 0
    
    yorum_sayisi = db.session.query(db.func.count(Yorum.YorumID)).join(Video).filter(
        Video.YukleyenTip=='Ogretmen',
        Video.YukleyenID==session['user_id']
    ).scalar() or 0
    
    # Tüm sınıfları çek
    siniflar = Sinif.query.all()
    
    # Diğer öğretmen, öğrenci ve admin videolarını çek
    diger_videolar = db.session.query(
        Video, Ogretmen, Ogrenci, Admin, Konu, Unite, Sinif, Ders
    ).outerjoin(
        Ogretmen, db.and_(Video.YukleyenTip == 'Ogretmen', Video.YukleyenID == Ogretmen.OgretmenID)
    ).outerjoin(
        Ogrenci, db.and_(Video.YukleyenTip == 'Ogrenci', Video.YukleyenID == Ogrenci.OgrenciID)
    ).outerjoin(
        Admin, db.and_(Video.YukleyenTip == 'Admin', Video.YukleyenID == Admin.AdminID)
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).join(
        Sinif, Ders.SinifID == Sinif.SinifID
    ).filter(
        db.or_(
            db.and_(Video.YukleyenTip == 'Ogretmen', Video.YukleyenID != session['user_id']),
            Video.YukleyenTip == 'Ogrenci',
            Video.YukleyenTip == 'Admin'  # Admin videolarını da dahil et
        )
    ).order_by(
        Sinif.SinifAdi,
        Ders.DersAdi,
        Unite.UniteNo,
        Konu.KonuNo,
        Video.YuklemeTarihi.desc()
    ).all()
    
    # Videoları sınıf ve ünite bazında grupla
    sinif_video_map = {}
    for video, ogretmen, ogrenci, admin, konu, unite, sinif, ders in diger_videolar:
        if sinif.SinifID not in sinif_video_map:
            sinif_video_map[sinif.SinifID] = {
                'sinif': sinif,
                'dersler': {}
            }
        
        if ders.DersID not in sinif_video_map[sinif.SinifID]['dersler']:
            sinif_video_map[sinif.SinifID]['dersler'][ders.DersID] = {
                'ders': ders,
                'uniteler': {}
            }
        
        if unite.UniteID not in sinif_video_map[sinif.SinifID]['dersler'][ders.DersID]['uniteler']:
            sinif_video_map[sinif.SinifID]['dersler'][ders.DersID]['uniteler'][unite.UniteID] = {
                'unite': unite,
                'videolar': []
            }
        
        # Yükleyeni belirle
        yukleyen = None
        if video.YukleyenTip == 'Ogretmen':
            yukleyen = ogretmen
        elif video.YukleyenTip == 'Ogrenci':
            yukleyen = ogrenci
        elif video.YukleyenTip == 'Admin':
            yukleyen = admin
        
        sinif_video_map[sinif.SinifID]['dersler'][ders.DersID]['uniteler'][unite.UniteID]['videolar'].append({
            'video': video,
            'yukleyen': yukleyen,
            'konu': konu
        })
    
    return render_template('ogretmen/dashboard.html', 
                         siniflar=siniflar,
                         video_sayisi=video_sayisi,
                         izlenme_sayisi=izlenme_sayisi,
                         yorum_sayisi=yorum_sayisi,
                         sinif_video_map=sinif_video_map,
                         get_embed_url=get_embed_url)

@app.route('/ogrenci/dashboard')
@login_required
def ogrenci_dashboard():
    if session['user_type'] != 'Ogrenci':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    ogrenci = Ogrenci.query.get(session['user_id'])
    
    # Tüm sınıfları ve dersleri al
    siniflar = Sinif.query.all()
    dersler = {}
    for sinif in siniflar:
        dersler[sinif.SinifID] = Ders.query.filter_by(SinifID=sinif.SinifID).all()
    
    # İzlenen videoları al
    izlenen_videolar = db.session.query(
        Video, Konu, Unite, Ders
    ).join(
        Izlenme, Video.VideoID == Izlenme.VideoID
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).filter(
        Izlenme.IzleyenID == session['user_id'],
        Izlenme.IzleyenTip == 'Ogrenci'
    ).order_by(Izlenme.IzlenmeTarihi.desc()).limit(5).all()
    
    # Beğenilen videoları al
    begenilen_videolar = db.session.query(
        Video, Konu, Unite, Ders
    ).join(
        Begenme, Video.VideoID == Begenme.VideoID
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).filter(
        Begenme.BegenenID == session['user_id'],
        Begenme.BegenenTip == 'Ogrenci'
    ).order_by(Begenme.BegenmeTarihi.desc()).limit(5).all()
    
    # İstatistikleri hesapla
    toplam_izlenme = Izlenme.query.filter_by(
        IzleyenID=session['user_id'],
        IzleyenTip='Ogrenci'
    ).count()
    
    toplam_begeni = Begenme.query.filter_by(
        BegenenID=session['user_id'],
        BegenenTip='Ogrenci'
    ).count()
    
    toplam_yorum = Yorum.query.filter_by(
        YorumYapanID=session['user_id'],
        YorumYapanTip='Ogrenci'
    ).count()
    
    return render_template('ogrenci/dashboard.html',
                         ogrenci=ogrenci,
                         siniflar=siniflar,
                         dersler=dersler,
                         izlenen_videolar=izlenen_videolar,
                         begenilen_videolar=begenilen_videolar,
                         toplam_izlenme=toplam_izlenme,
                         toplam_begeni=toplam_begeni,
                         toplam_yorum=toplam_yorum)

@app.route('/ogretmen/ders/<int:ders_id>')
@login_required
def ogretmen_ders(ders_id):
    if session['user_type'] != 'Ogretmen':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
        
    # Dersi ve ilgili bilgileri çek
    ders = Ders.query.get_or_404(ders_id)
    
    # Üniteleri çek
    uniteler = Unite.query.filter_by(DersID=ders_id).order_by(Unite.UniteNo).all()
    
    # Her ünite için konuları ve videoları çek
    for unite in uniteler:
        unite.konular = Konu.query.filter_by(UniteID=unite.UniteID).order_by(Konu.KonuNo).all()
        # Her konu için öğretmenin videolarını çek
        for konu in unite.konular:
            konu.videolar = Video.query.filter_by(
                KonuID=konu.KonuID,
                YukleyenTip='Ogretmen',
                YukleyenID=session['user_id']
            ).order_by(Video.YuklemeTarihi.desc()).all()
    
    return render_template('ogretmen/ders.html', 
                         ders=ders, 
                         uniteler=uniteler,
                         get_embed_url=get_embed_url)

@app.route('/video/guncelle/<int:video_id>', methods=['POST'])
@login_required
def video_guncelle(video_id):
    if session['user_type'] != 'Ogretmen':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    video = Video.query.get_or_404(video_id)
    
    # Video sahibi kontrolü
    if video.YukleyenID != session['user_id'] or video.YukleyenTip != 'Ogretmen':
        flash('Bu videoyu düzenleme yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    # Form verilerini al
    baslik = request.form.get('baslik')
    video_url = request.form.get('video_url')
    aciklama = request.form.get('aciklama')
    
    # Videoyu güncelle
    video.Baslik = baslik
    video.VideoURL = video_url
    video.Aciklama = aciklama
    
    try:
        db.session.commit()
        flash('Video başarıyla güncellendi!', 'success')
    except:
        db.session.rollback()
        flash('Video güncellenirken bir hata oluştu!', 'error')
    
    return redirect(url_for('ogretmen_ders', ders_id=video.konu.unite.DersID))

@app.route('/video/sil/<int:video_id>', methods=['POST'])
@login_required
def video_sil(video_id):
    if session['user_type'] != 'Ogretmen':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    video = Video.query.get_or_404(video_id)
    
    # Video sahibi kontrolü
    if video.YukleyenID != session['user_id'] or video.YukleyenTip != 'Ogretmen':
        flash('Bu videoyu silme yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    ders_id = video.konu.unite.DersID
    
    try:
        db.session.delete(video)
        db.session.commit()
        flash('Video başarıyla silindi!', 'success')
    except:
        db.session.rollback()
        flash('Video silinirken bir hata oluştu!', 'error')
    
    return redirect(url_for('ogretmen_ders', ders_id=ders_id))

@app.route('/video/ekle/<int:konu_id>', methods=['POST'])
@login_required
def video_ekle(konu_id):
    if session['user_type'] != 'Ogretmen':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    konu = Konu.query.get_or_404(konu_id)
    
    # Form verilerini al
    baslik = request.form.get('baslik')
    video_url = request.form.get('video_url')
    aciklama = request.form.get('aciklama')
    
    # Yeni video oluştur
    yeni_video = Video(
        Baslik=baslik,
        VideoURL=video_url,
        Aciklama=aciklama,
        KonuID=konu_id,
        YukleyenTip='Ogretmen',
        YukleyenID=session['user_id'],
        AktifMi=False  # Varsayılan olarak pasif olarak ayarla
    )
    
    try:
        db.session.add(yeni_video)
        db.session.commit()
        flash('Video başarıyla eklendi! Admin onayından sonra yayınlanacaktır.', 'success')
    except:
        db.session.rollback()
        flash('Video eklenirken bir hata oluştu!', 'error')
    
    return redirect(url_for('ogretmen_ders', ders_id=konu.unite.DersID))

@app.route('/ogretmen/profil', methods=['GET', 'POST'])
@login_required
def ogretmen_profil():
    if session['user_type'] != 'Ogretmen':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    ogretmen = Ogretmen.query.get(session['user_id'])
    
    if request.method == 'POST':
        eski_sifre = request.form.get('eski_sifre')
        yeni_sifre = request.form.get('yeni_sifre')
        yeni_sifre_tekrar = request.form.get('yeni_sifre_tekrar')
        
        if eski_sifre and yeni_sifre and yeni_sifre_tekrar:
            # Şimdilik direkt string karşılaştırması yapalım
            if ogretmen.Sifre == eski_sifre:
                if yeni_sifre == yeni_sifre_tekrar:
                    ogretmen.Sifre = yeni_sifre  # Yeni şifreyi direkt kaydedelim
                    try:
                        db.session.commit()
                        flash('Şifreniz başarıyla güncellendi!', 'success')
                    except Exception as e:
                        print("Hata:", str(e))
                        db.session.rollback()
                        flash('Şifre güncellenirken bir hata oluştu!', 'error')
                else:
                    flash('Yeni şifreler eşleşmiyor!', 'error')
                    return redirect(url_for('ogretmen_profil'))
            else:
                flash('Mevcut şifreniz yanlış!', 'error')
                return redirect(url_for('ogretmen_profil'))
        else:
            # Profil bilgileri güncelleme
            ogretmen.Ad = request.form.get('ad')
            ogretmen.Soyad = request.form.get('soyad')
            ogretmen.Email = request.form.get('email')
            ogretmen.Brans = request.form.get('brans')
            
            try:
                db.session.commit()
                flash('Profiliniz başarıyla güncellendi!', 'success')
            except:
                db.session.rollback()
                flash('Profil güncellenirken bir hata oluştu!', 'error')
            
            return redirect(url_for('ogretmen_profil'))
    
    # İstatistikleri hesapla
    video_sayisi = Video.query.filter_by(
        YukleyenTip='Ogretmen',
        YukleyenID=session['user_id']
    ).count()
    
    izlenme_sayisi = db.session.query(db.func.count(Izlenme.IzlenmeID)).join(Video).filter(
        Video.YukleyenTip=='Ogretmen',
        Video.YukleyenID==session['user_id']
    ).scalar() or 0
    
    yorum_sayisi = db.session.query(db.func.count(Yorum.YorumID)).join(Video).filter(
        Video.YukleyenTip=='Ogretmen',
        Video.YukleyenID==session['user_id']
    ).scalar() or 0
    
    return render_template('ogretmen/profil.html',
                         ogretmen=ogretmen,
                         video_sayisi=video_sayisi,
                         izlenme_sayisi=izlenme_sayisi,
                         yorum_sayisi=yorum_sayisi)

@app.route('/admin/video/onayla/<int:video_id>', methods=['POST'])
@login_required
def video_onayla(video_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    video = Video.query.get_or_404(video_id)
    video.AktifMi = True  # Videoyu aktif yap
    video.ReddetmeSebebi = None  # Reddetme sebebini NULL yap
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Video onaylandı!'})
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Bir hata oluştu!'})

@app.route('/admin/video/reddet/<int:video_id>', methods=['POST'])
@login_required
def video_reddet(video_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    video = Video.query.get_or_404(video_id)
    video.AktifMi = False  # Videoyu pasif yap
    video.ReddetmeSebebi = 'Admin tarafından reddedildi'  # Reddetme sebebini ekle
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Video reddedildi!'})
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Bir hata oluştu!'})

@app.route('/admin/sinif/ekle', methods=['POST'])
@login_required
def sinif_ekle():
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    sinif_adi = request.form.get('sinif_adi')
    aciklama = request.form.get('aciklama')
    
    if not sinif_adi:
        return jsonify({'success': False, 'message': 'Sınıf adı boş olamaz!'})
    
    # Aynı isimde sınıf var mı kontrol et
    if Sinif.query.filter_by(SinifAdi=sinif_adi).first():
        return jsonify({'success': False, 'message': 'Bu isimde bir sınıf zaten var!'})
    
    yeni_sinif = Sinif(
        SinifAdi=sinif_adi,
        Aciklama=aciklama
    )
    
    try:
        db.session.add(yeni_sinif)
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Sınıf başarıyla eklendi!',
            'sinif': {
                'id': yeni_sinif.SinifID,
                'adi': yeni_sinif.SinifAdi,
                'aciklama': yeni_sinif.Aciklama,
                'ogrenci_sayisi': 0,
                'ders_sayisi': 0
            }
        })
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Sınıf eklenirken bir hata oluştu!'})

@app.route('/admin/sinif/sil/<int:sinif_id>', methods=['POST'])
@login_required
def sinif_sil(sinif_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    sinif = Sinif.query.get_or_404(sinif_id)
    
    try:
        # Önce ilişkili kayıtları sil
        OgretmenDers.query.filter_by(SinifID=sinif_id).delete()
        Ders.query.filter_by(SinifID=sinif_id).delete()
        db.session.delete(sinif)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sınıf başarıyla silindi!'})
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Sınıf silinirken bir hata oluştu!'})

@app.route('/admin/sinif/guncelle/<int:sinif_id>', methods=['POST'])
@login_required
def sinif_guncelle(sinif_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    sinif = Sinif.query.get_or_404(sinif_id)
    sinif_adi = request.form.get('sinif_adi')
    aciklama = request.form.get('aciklama')
    
    if not sinif_adi:
        return jsonify({'success': False, 'message': 'Sınıf adı boş olamaz!'})
    
    # Aynı isimde başka sınıf var mı kontrol et
    mevcut_sinif = Sinif.query.filter(
        Sinif.SinifAdi == sinif_adi,
        Sinif.SinifID != sinif_id
    ).first()
    
    if mevcut_sinif:
        return jsonify({'success': False, 'message': 'Bu isimde bir sınıf zaten var!'})
    
    try:
        sinif.SinifAdi = sinif_adi
        sinif.Aciklama = aciklama
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sınıf başarıyla güncellendi!',
            'sinif': {
                'id': sinif.SinifID,
                'adi': sinif.SinifAdi,
                'aciklama': sinif.Aciklama
            }
        })
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Sınıf güncellenirken bir hata oluştu!'})

@app.route('/admin/mesajlar')
@login_required
def admin_mesajlar():
    if session['user_type'] != 'Admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    # Gelen mesajları al
    mesajlar = db.session.query(
        Mesaj, Ogretmen, Ogrenci, Admin
    ).outerjoin(
        Ogretmen, db.and_(Mesaj.GonderenTip == 'Ogretmen', Mesaj.GonderenID == Ogretmen.OgretmenID)
    ).outerjoin(
        Ogrenci, db.and_(Mesaj.GonderenTip == 'Ogrenci', Mesaj.GonderenID == Ogrenci.OgrenciID)
    ).outerjoin(
        Admin, db.and_(Mesaj.GonderenTip == 'Admin', Mesaj.GonderenID == Admin.AdminID)
    ).filter(
        Mesaj.AliciTip == 'Admin',
        Mesaj.AliciID == session['user_id']
    ).order_by(
        Mesaj.GondermeTarihi.desc()
    ).all()
    
    return render_template('admin/mesajlar.html', mesajlar=mesajlar)

@app.route('/admin/mesaj/cevapla/<int:mesaj_id>', methods=['POST'])
@login_required
def mesaj_cevapla(mesaj_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    mesaj = Mesaj.query.get_or_404(mesaj_id)
    cevap = request.form.get('cevap')
    
    if not cevap:
        return jsonify({'success': False, 'message': 'Cevap boş olamaz!'})
    
    # Yeni cevap mesajı oluştur
    yeni_mesaj = Mesaj(
        GonderenTip='Admin',
        GonderenID=session['user_id'],
        AliciTip=mesaj.GonderenTip,
        AliciID=mesaj.GonderenID,
        MesajIcerik=cevap,
        CevaplananMesajID=mesaj_id
    )
    
    try:
        db.session.add(yeni_mesaj)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mesaj başarıyla gönderildi!'})
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Mesaj gönderilirken bir hata oluştu!'})

@app.route('/admin/profil')
@login_required
def admin_profil():
    if session['user_type'] != 'Admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    admin = Admin.query.get(session['user_id'])
    
    # İstatistikleri hesapla
    onaylanan_video_sayisi = Video.query.filter_by(AktifMi=True).count()
    reddedilen_video_sayisi = Video.query.filter(Video.ReddetmeSebebi != None).count()
    mesaj_sayisi = Mesaj.query.filter_by(AliciTip='Admin', AliciID=session['user_id']).count()
    
    return render_template('admin/profil.html',
                         admin=admin,
                         onaylanan_video_sayisi=onaylanan_video_sayisi,
                         reddedilen_video_sayisi=reddedilen_video_sayisi,
                         mesaj_sayisi=mesaj_sayisi)

@app.route('/admin/profil/guncelle', methods=['POST'])
@login_required
def admin_profil_guncelle():
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    admin = Admin.query.get(session['user_id'])
    
    # Form verilerini al
    ad = request.form.get('ad')
    soyad = request.form.get('soyad')
    kullanici_adi = request.form.get('kullanici_adi')
    email = request.form.get('email')
    
    # Kullanıcı adı ve email benzersiz olmalı
    if Admin.query.filter(Admin.KullaniciAdi == kullanici_adi, Admin.AdminID != admin.AdminID).first():
        flash('Bu kullanıcı adı zaten kullanılıyor!', 'error')
        return redirect(url_for('admin_profil'))
    
    if Admin.query.filter(Admin.Email == email, Admin.AdminID != admin.AdminID).first():
        flash('Bu e-posta adresi zaten kullanılıyor!', 'error')
        return redirect(url_for('admin_profil'))
    
    try:
        admin.Ad = ad
        admin.Soyad = soyad
        admin.KullaniciAdi = kullanici_adi
        admin.Email = email
        
        db.session.commit()
        flash('Profil bilgileriniz başarıyla güncellendi!', 'success')
    except:
        db.session.rollback()
        flash('Profil güncellenirken bir hata oluştu!', 'error')
    
    return redirect(url_for('admin_profil'))

@app.route('/admin/profil/sifre-guncelle', methods=['POST'])
@login_required
def admin_sifre_guncelle():
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    admin = Admin.query.get(session['user_id'])
    
    mevcut_sifre = request.form.get('mevcut_sifre')
    yeni_sifre = request.form.get('yeni_sifre')
    yeni_sifre_tekrar = request.form.get('yeni_sifre_tekrar')
    
    # Mevcut şifreyi kontrol et
    if not check_password_hash(admin.Sifre, mevcut_sifre):
        flash('Mevcut şifreniz yanlış!', 'error')
        return redirect(url_for('admin_profil'))
    
    # Yeni şifrelerin eşleştiğini kontrol et
    if yeni_sifre != yeni_sifre_tekrar:
        flash('Yeni şifreler eşleşmiyor!', 'error')
        return redirect(url_for('admin_profil'))
    
    try:
        admin.Sifre = generate_password_hash(yeni_sifre)
        db.session.commit()
        flash('Şifreniz başarıyla güncellendi!', 'success')
    except:
        db.session.rollback()
        flash('Şifre güncellenirken bir hata oluştu!', 'error')
    
    return redirect(url_for('admin_profil'))

@app.route('/admin/dersler/<int:sinif_id>')
@login_required
def admin_dersler(sinif_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    dersler = Ders.query.filter_by(SinifID=sinif_id).all()
    return jsonify({
        'success': True,
        'dersler': [{'id': ders.DersID, 'adi': ders.DersAdi} for ders in dersler]
    })

@app.route('/admin/uniteler/<int:ders_id>')
@login_required
def admin_uniteler(ders_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    uniteler = Unite.query.filter_by(DersID=ders_id).all()
    return jsonify({
        'success': True,
        'uniteler': [{'id': unite.UniteID, 'adi': unite.UniteAdi} for unite in uniteler]
    })

@app.route('/admin/konular/<int:unite_id>')
@login_required
def admin_konular(unite_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    konular = Konu.query.filter_by(UniteID=unite_id).all()
    return jsonify({
        'success': True,
        'konular': [{'id': konu.KonuID, 'adi': konu.KonuAdi} for konu in konular]
    })

@app.route('/admin/video/ekle', methods=['POST'])
@login_required
def admin_video_ekle():
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    konu_id = request.form.get('konu_id')
    baslik = request.form.get('baslik')
    video_url = request.form.get('video_url')
    aciklama = request.form.get('aciklama')
    
    if not all([konu_id, baslik, video_url]):
        return jsonify({'success': False, 'message': 'Tüm alanları doldurun!'})
    
    try:
        yeni_video = Video(
            Baslik=baslik,
            VideoURL=video_url,
            KonuID=konu_id,
            YukleyenTip='Admin',
            YukleyenID=session['user_id'],
            Aciklama=aciklama,
            AktifMi=True
        )
        
        db.session.add(yeni_video)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Video başarıyla eklendi!'
        })
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Video eklenirken bir hata oluştu!'})

@app.route('/admin/videolarim')
@login_required
def admin_videolarim():
    if session['user_type'] != 'Admin':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    # Admin'in videolarını al
    videolar = db.session.query(
        Video, Admin, Konu, Unite, Sinif, Ders
    ).join(
        Admin, 
        (Admin.AdminID == Video.YukleyenID) & (Video.YukleyenTip == 'Admin')
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).join(
        Sinif, Ders.SinifID == Sinif.SinifID
    ).filter(
        Video.YukleyenID == session['user_id']
    ).order_by(Video.YuklemeTarihi.desc()).all()
    
    return render_template('admin/videolarim.html', videolar=videolar)

@app.route('/admin/video/detay/<int:video_id>')
@login_required
def admin_video_detay(video_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    video = db.session.query(
        Video, Konu, Unite, Ders
    ).join(
        Konu, Video.KonuID == Konu.KonuID
    ).join(
        Unite, Konu.UniteID == Unite.UniteID
    ).join(
        Ders, Unite.DersID == Ders.DersID
    ).filter(Video.VideoID == video_id).first()
    
    if not video:
        return jsonify({'success': False, 'message': 'Video bulunamadı!'})
    
    return jsonify({
        'success': True,
        'video': {
            'id': video.Video.VideoID,
            'baslik': video.Video.Baslik,
            'url': video.Video.VideoURL,
            'aciklama': video.Video.Aciklama,
            'embed_url': get_embed_url(video.Video.VideoURL),
            'konu': video.Konu.KonuAdi,
            'unite': video.Unite.UniteAdi,
            'ders': video.Ders.DersAdi
        }
    })

@app.route('/admin/video/guncelle/<int:video_id>', methods=['POST'])
@login_required
def admin_video_guncelle(video_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    video = Video.query.get(video_id)
    if not video or video.YukleyenID != session['user_id']:
        return jsonify({'success': False, 'message': 'Video bulunamadı!'})
    
    try:
        video.Baslik = request.form.get('baslik')
        video.VideoURL = request.form.get('video_url')
        video.Aciklama = request.form.get('aciklama')
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Video başarıyla güncellendi!'
        })
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Video güncellenirken bir hata oluştu!'})

@app.route('/admin/video/sil/<int:video_id>', methods=['POST'])
@login_required
def admin_video_sil(video_id):
    if session['user_type'] != 'Admin':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    video = Video.query.get(video_id)
    if not video or video.YukleyenID != session['user_id']:
        return jsonify({'success': False, 'message': 'Video bulunamadı!'})
    
    try:
        db.session.delete(video)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Video başarıyla silindi!'
        })
    except:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Video silinirken bir hata oluştu!'})

# Veritabanı modelleri
class Sinif(db.Model):
    __tablename__ = 'Sinif'
    SinifID = db.Column(db.Integer, primary_key=True)
    SinifAdi = db.Column(db.String(50), nullable=False)
    Aciklama = db.Column(db.String(200))
    dersler = db.relationship('Ders', backref='sinif', lazy=True)

class Ders(db.Model):
    __tablename__ = 'Ders'
    DersID = db.Column(db.Integer, primary_key=True)
    DersAdi = db.Column(db.String(100), nullable=False)
    SinifID = db.Column(db.Integer, db.ForeignKey('Sinif.SinifID'))
    Aciklama = db.Column(db.String(500))

class Video(db.Model):
    __tablename__ = 'Video'
    VideoID = db.Column(db.Integer, primary_key=True)
    Baslik = db.Column(db.String(200), nullable=False)
    VideoURL = db.Column(db.String(500), nullable=False)
    KonuID = db.Column(db.Integer, db.ForeignKey('Konu.KonuID'))
    YukleyenTip = db.Column(db.String(20), nullable=False)
    YukleyenID = db.Column(db.Integer, nullable=False)
    YuklemeTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    Aciklama = db.Column(db.String(1000))
    AktifMi = db.Column(db.Boolean, default=False)  # Varsayılan olarak False
    ReddetmeSebebi = db.Column(db.String(500))  # Reddetme sebebi için yeni alan

    # İlişkiler
    konu = db.relationship('Konu', backref='videolar', lazy=True)

class Konu(db.Model):
    __tablename__ = 'Konu'
    KonuID = db.Column(db.Integer, primary_key=True)
    UniteID = db.Column(db.Integer, db.ForeignKey('Unite.UniteID'))
    KonuAdi = db.Column(db.String(100), nullable=False)
    KonuNo = db.Column(db.Integer, nullable=False)
    Aciklama = db.Column(db.String(500))

class Begenme(db.Model):
    __tablename__ = 'Begenme'
    BegenmeID = db.Column(db.Integer, primary_key=True)
    VideoID = db.Column(db.Integer, db.ForeignKey('Video.VideoID'))
    BegenenTip = db.Column(db.String(20), nullable=False)  # 'Admin', 'Ogretmen' veya 'Ogrenci'
    BegenenID = db.Column(db.Integer, nullable=False)
    BegenmeTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())

    # İlişkiler
    video = db.relationship('Video', backref='begeniler', lazy=True)

class Izlenme(db.Model):
    __tablename__ = 'Izlenme'
    IzlenmeID = db.Column(db.Integer, primary_key=True)
    VideoID = db.Column(db.Integer, db.ForeignKey('Video.VideoID'))
    IzleyenTip = db.Column(db.String(20), nullable=False)  # 'Admin', 'Ogretmen' veya 'Ogrenci'
    IzleyenID = db.Column(db.Integer, nullable=False)
    IzlenmeTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())

    # İlişkiler
    video = db.relationship('Video', backref='izlenmeler', lazy=True)

class Unite(db.Model):
    __tablename__ = 'Unite'
    UniteID = db.Column(db.Integer, primary_key=True)
    DersID = db.Column(db.Integer, db.ForeignKey('Ders.DersID'))
    UniteAdi = db.Column(db.String(100), nullable=False)
    UniteNo = db.Column(db.Integer, nullable=False)
    Aciklama = db.Column(db.String(500))

    # İlişkiler
    konular = db.relationship('Konu', backref='unite', lazy=True)
    ders = db.relationship('Ders', backref='uniteler', lazy=True)

class Ogrenci(db.Model):
    __tablename__ = 'Ogrenci'
    OgrenciID = db.Column(db.Integer, primary_key=True)
    KullaniciAdi = db.Column(db.String(50), nullable=False)
    Sifre = db.Column(db.String(100), nullable=False)
    Ad = db.Column(db.String(50), nullable=False)
    Soyad = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    SinifID = db.Column(db.Integer, db.ForeignKey('Sinif.SinifID'))
    KayitTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    AktifMi = db.Column(db.Boolean, default=True)

class Ogretmen(db.Model):
    __tablename__ = 'Ogretmen'
    OgretmenID = db.Column(db.Integer, primary_key=True)
    KullaniciAdi = db.Column(db.String(50), nullable=False)
    Sifre = db.Column(db.String(100), nullable=False)
    Ad = db.Column(db.String(50), nullable=False)
    Soyad = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Brans = db.Column(db.String(50), nullable=False)
    KayitTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    AktifMi = db.Column(db.Boolean, default=True)

class Admin(db.Model):
    __tablename__ = 'Admin'
    AdminID = db.Column(db.Integer, primary_key=True)
    KullaniciAdi = db.Column(db.String(50), nullable=False)
    Sifre = db.Column(db.String(100), nullable=False)
    Ad = db.Column(db.String(50), nullable=False)
    Soyad = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    KayitTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    AktifMi = db.Column(db.Boolean, default=True)

class Yorum(db.Model):
    __tablename__ = 'Yorum'
    YorumID = db.Column(db.Integer, primary_key=True)
    VideoID = db.Column(db.Integer, db.ForeignKey('Video.VideoID'))
    YorumMetni = db.Column(db.String(1000), nullable=False)
    YorumYapanTip = db.Column(db.String(20), nullable=False)  # 'Admin', 'Ogretmen' veya 'Ogrenci'
    YorumYapanID = db.Column(db.Integer, nullable=False)
    YorumTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    AktifMi = db.Column(db.Boolean, default=True)
    
    # İlişkiler
    video = db.relationship('Video', backref=db.backref('yorumlar', lazy=True))

# Öğretmen-Ders ilişki tablosu
class OgretmenDers(db.Model):
    __tablename__ = 'OgretmenDers'
    OgretmenDersID = db.Column(db.Integer, primary_key=True)
    OgretmenID = db.Column(db.Integer, db.ForeignKey('Ogretmen.OgretmenID'))
    DersID = db.Column(db.Integer, db.ForeignKey('Ders.DersID'))
    SinifID = db.Column(db.Integer, db.ForeignKey('Sinif.SinifID'))
    
    # İlişkiler
    ogretmen = db.relationship('Ogretmen', backref='ogretmen_dersler')
    ders = db.relationship('Ders', backref='ogretmen_dersler')
    sinif = db.relationship('Sinif', backref='ogretmen_dersler')

class Mesaj(db.Model):
    __tablename__ = 'Mesaj'
    MesajID = db.Column(db.Integer, primary_key=True)
    GonderenTip = db.Column(db.String(20), nullable=False)  # 'Admin', 'Ogretmen' veya 'Ogrenci'
    GonderenID = db.Column(db.Integer, nullable=False)
    AliciTip = db.Column(db.String(20), nullable=False)  # 'Admin', 'Ogretmen' veya 'Ogrenci'
    AliciID = db.Column(db.Integer, nullable=False)
    MesajIcerik = db.Column(db.String(1000), nullable=False)
    GondermeTarihi = db.Column(db.DateTime, default=db.func.current_timestamp())
    CevaplananMesajID = db.Column(db.Integer, db.ForeignKey('Mesaj.MesajID'), nullable=True)
    
    # İlişkiler
    cevaplanan_mesaj = db.relationship('Mesaj', remote_side=[MesajID], backref='cevaplar')

@app.route('/ogrenci/profil', methods=['GET', 'POST'])
@login_required
def ogrenci_profil():
    if session['user_type'] != 'Ogrenci':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    ogrenci = Ogrenci.query.get(session['user_id'])
    
    if request.method == 'POST':
        if 'yeni_sifre' in request.form:  # Şifre değiştirme formu
            mevcut_sifre = request.form.get('mevcut_sifre')
            yeni_sifre = request.form.get('yeni_sifre')
            
            ogrenci = Ogrenci.query.get(session['user_id'])
            if ogrenci.Sifre == mevcut_sifre:  # Direkt şifre kontrolü
                ogrenci.Sifre = yeni_sifre  # Yeni şifreyi direkt kaydet
                db.session.commit()
                flash('Şifreniz başarıyla güncellendi!', 'success')
            else:
                flash('Mevcut şifreniz hatalı!', 'danger')
        else:
            # Profil bilgilerini güncelle
            ogrenci.Ad = request.form.get('ad')
            ogrenci.Soyad = request.form.get('soyad')
            ogrenci.Email = request.form.get('email')
            
            try:
                db.session.commit()
                flash('Profil bilgileriniz başarıyla güncellendi!', 'success')
            except:
                db.session.rollback()
                flash('Profil güncellenirken bir hata oluştu!', 'error')
        
        return redirect(url_for('ogrenci_profil'))
    
    # İstatistikleri hesapla
    toplam_izlenme = Izlenme.query.filter_by(
        IzleyenID=session['user_id'],
        IzleyenTip='Ogrenci'
    ).count()
    
    toplam_begeni = Begenme.query.filter_by(
        BegenenID=session['user_id'],
        BegenenTip='Ogrenci'
    ).count()
    
    toplam_yorum = Yorum.query.filter_by(
        YorumYapanID=session['user_id'],
        YorumYapanTip='Ogrenci'
    ).count()
    
    return render_template('ogrenci/profil.html',
                         ogrenci=ogrenci,
                         toplam_izlenme=toplam_izlenme,
                         toplam_begeni=toplam_begeni,
                         toplam_yorum=toplam_yorum)

@app.route('/ogrenci/ders/<int:ders_id>')
@login_required
def ogrenci_ders(ders_id):
    if session['user_type'] != 'Ogrenci':
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    ders = Ders.query.get_or_404(ders_id)
    uniteler = Unite.query.filter_by(DersID=ders_id).all()
    
    # Her ünite için konuları ve videoları al
    unite_konular = {}
    for unite in uniteler:
        konular = Konu.query.filter_by(UniteID=unite.UniteID).all()
        unite_konular[unite.UniteID] = {
            'konular': konular,
            'videolar': {}
        }
        for konu in konular:
            videolar = Video.query.filter_by(KonuID=konu.KonuID, AktifMi=True).all()
            # Video nesnelerini sözlük formatına dönüştür
            unite_konular[unite.UniteID]['videolar'][konu.KonuID] = [{
                'VideoID': video.VideoID,
                'Baslik': video.Baslik,
                'VideoURL': get_embed_url(video.VideoURL),  # URL'yi embed formatına dönüştür
                'Aciklama': video.Aciklama,
                'YuklemeTarihi': video.YuklemeTarihi.strftime('%d.%m.%Y'),
                'izlenme_sayisi': video.izlenme_sayisi if hasattr(video, 'izlenme_sayisi') else 0
            } for video in videolar]
    
    return render_template('ogrenci/ders.html',
                         ders=ders,
                         uniteler=uniteler,
                         unite_konular=unite_konular)

@app.route('/video/<int:video_id>/yorumlar')
@login_required
def video_yorumlar(video_id):
    try:
        yorumlar = db.session.query(
            Yorum,
            case(
                (Yorum.YorumYapanTip == 'Ogrenci', Ogrenci.Ad + ' ' + Ogrenci.Soyad),
                (Yorum.YorumYapanTip == 'Ogretmen', Ogretmen.Ad + ' ' + Ogretmen.Soyad),
                (Yorum.YorumYapanTip == 'Admin', Admin.Ad + ' ' + Admin.Soyad)
            ).label('YorumYapan')
        ).outerjoin(
            Ogrenci, 
            (Yorum.YorumYapanID == Ogrenci.OgrenciID) & (Yorum.YorumYapanTip == 'Ogrenci')
        ).outerjoin(
            Ogretmen,
            (Yorum.YorumYapanID == Ogretmen.OgretmenID) & (Yorum.YorumYapanTip == 'Ogretmen')
        ).outerjoin(
            Admin,
            (Yorum.YorumYapanID == Admin.AdminID) & (Yorum.YorumYapanTip == 'Admin')
        ).filter(
            Yorum.VideoID == video_id,
            Yorum.AktifMi == True
        ).order_by(Yorum.YorumTarihi.desc()).all()
        
        return jsonify({
            'success': True,
            'yorumlar': [{
                'YorumID': yorum.Yorum.YorumID,
                'Yorum': yorum.Yorum.YorumMetni,
                'YorumTarihi': yorum.Yorum.YorumTarihi.strftime('%d.%m.%Y %H:%M'),
                'YorumYapan': yorum.YorumYapan
            } for yorum in yorumlar]
        })
        
    except Exception as e:
        print(f"Hata: {str(e)}")  # Hata ayıklama için
        return jsonify({
            'success': False,
            'message': 'Yorumlar yüklenirken bir hata oluştu!'
        })

@app.route('/video/<int:video_id>/yorum-yap', methods=['POST'])
@login_required
def video_yorum_yap(video_id):
    try:
        data = request.get_json()
        yorum_metni = data.get('yorum')
        
        if not yorum_metni:
            return jsonify({'success': False, 'message': 'Yorum metni boş olamaz!'})
        
        # Yeni yorum oluştur
        yeni_yorum = Yorum(
            VideoID=video_id,
            YorumYapanTip=session['user_type'],
            YorumYapanID=session['user_id'],
            YorumMetni=yorum_metni,
            YorumTarihi=datetime.now(),
            AktifMi=True
        )
        
        db.session.add(yeni_yorum)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Yorum başarıyla eklendi!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Hata: {str(e)}")  # Hata ayıklama için
        return jsonify({
            'success': False,
            'message': 'Yorum eklenirken bir hata oluştu!'
        })

@app.route('/video/<int:video_id>/izlenme-durumu')
@login_required
def video_izlenme_durumu(video_id):
    izlendi = Izlenme.query.filter_by(
        VideoID=video_id,
        IzleyenID=session['user_id'],
        IzleyenTip=session['user_type']
    ).first() is not None
    
    return jsonify({'izlendi': izlendi})

@app.route('/video/<int:video_id>/begenilme-durumu')
@login_required
def video_begenilme_durumu(video_id):
    begenildi = Begenme.query.filter_by(
        VideoID=video_id,
        BegenenID=session['user_id'],
        BegenenTip=session['user_type']
    ).first() is not None
    
    return jsonify({'begenildi': begenildi})

@app.route('/video/<int:video_id>/izle', methods=['POST'])
@login_required
def video_izle(video_id):
    izlenme = Izlenme.query.filter_by(
        VideoID=video_id,
        IzleyenID=session['user_id'],
        IzleyenTip=session['user_type']
    ).first()
    
    if not izlenme:
        izlenme = Izlenme(
            VideoID=video_id,
            IzleyenID=session['user_id'],
            IzleyenTip=session['user_type'],
            IzlenmeTarihi=datetime.now()
        )
        db.session.add(izlenme)
        db.session.commit()
    
    # Toplam izlenme sayısını döndür
    izlenme_sayisi = Izlenme.query.filter_by(VideoID=video_id).count()
    
    return jsonify({
        'success': True,
        'izlenme_sayisi': izlenme_sayisi
    })

@app.route('/video/<int:video_id>/begen-toggle', methods=['POST'])
@login_required
def video_begen_toggle(video_id):
    begenme = Begenme.query.filter_by(
        VideoID=video_id,
        BegenenID=session['user_id'],
        BegenenTip=session['user_type']
    ).first()
    
    if begenme:
        db.session.delete(begenme)
    else:
        begenme = Begenme(
            VideoID=video_id,
            BegenenID=session['user_id'],
            BegenenTip=session['user_type'],
            BegenmeTarihi=datetime.now()
        )
        db.session.add(begenme)
    
    db.session.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 