-- Admin Tablosu
CREATE TABLE Admin (
    AdminID INT PRIMARY KEY IDENTITY(1,1),
    KullaniciAdi NVARCHAR(50) NOT NULL,
    Sifre NVARCHAR(100) NOT NULL,
    Ad NVARCHAR(50) NOT NULL,
    Soyad NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) UNIQUE NOT NULL,
    KayitTarihi DATETIME DEFAULT GETDATE(),
    AktifMi BIT DEFAULT 1
)

-- Ogretmen Tablosu
CREATE TABLE Ogretmen (
    OgretmenID INT PRIMARY KEY IDENTITY(1,1),
    KullaniciAdi NVARCHAR(50) NOT NULL,
    Sifre NVARCHAR(500) NOT NULL,
    Ad NVARCHAR(50) NOT NULL,
    Soyad NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) UNIQUE NOT NULL,
    Brans NVARCHAR(50) NOT NULL,
    KayitTarihi DATETIME DEFAULT GETDATE(),
    AktifMi BIT DEFAULT 1
)

-- Ogrenci Tablosu
CREATE TABLE Ogrenci (
    OgrenciID INT PRIMARY KEY IDENTITY(1,1),
    KullaniciAdi NVARCHAR(50) NOT NULL,
    Sifre NVARCHAR(500) NOT NULL,
    Ad NVARCHAR(50) NOT NULL,
    Soyad NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) UNIQUE NOT NULL,
    KayitTarihi DATETIME DEFAULT GETDATE(),
    AktifMi BIT DEFAULT 1
)

-- Sinif Tablosu
CREATE TABLE Sinif (
    SinifID INT PRIMARY KEY IDENTITY(1,1),
    SinifAdi NVARCHAR(50) NOT NULL,
    Aciklama NVARCHAR(200)
)

-- Ders Tablosu
CREATE TABLE Ders (
    DersID INT PRIMARY KEY IDENTITY(1,1),
    DersAdi NVARCHAR(100) NOT NULL,
    SinifID INT FOREIGN KEY REFERENCES Sinif(SinifID),
    Aciklama NVARCHAR(500)
)

-- Unite Tablosu
CREATE TABLE Unite (
    UniteID INT PRIMARY KEY IDENTITY(1,1),
    DersID INT FOREIGN KEY REFERENCES Ders(DersID),
    UniteAdi NVARCHAR(100) NOT NULL,
    UniteNo INT NOT NULL,
    Aciklama NVARCHAR(500)
)

-- Konu Tablosu
CREATE TABLE Konu (
    KonuID INT PRIMARY KEY IDENTITY(1,1),
    UniteID INT FOREIGN KEY REFERENCES Unite(UniteID),
    KonuAdi NVARCHAR(100) NOT NULL,
    KonuNo INT NOT NULL,
    Aciklama NVARCHAR(500)
)

-- Video Tablosu
CREATE TABLE Video (
    VideoID INT PRIMARY KEY IDENTITY(1,1),
    Baslik NVARCHAR(200) NOT NULL,
    VideoURL NVARCHAR(500) NOT NULL,
    KonuID INT FOREIGN KEY REFERENCES Konu(KonuID),
    YukleyenTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    YukleyenID INT NOT NULL,
    YuklemeTarihi DATETIME DEFAULT GETDATE(),
    Aciklama NVARCHAR(1000),
    AktifMi BIT DEFAULT 1
)

-- Yorum Tablosu
CREATE TABLE Yorum (
    YorumID INT PRIMARY KEY IDENTITY(1,1),
    VideoID INT FOREIGN KEY REFERENCES Video(VideoID),
    YorumYapanTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    YorumYapanID INT NOT NULL,
    YorumMetni NVARCHAR(500) NOT NULL,
    YorumTarihi DATETIME DEFAULT GETDATE(),
    AktifMi BIT DEFAULT 1
)

-- Begenme Tablosu
CREATE TABLE Begenme (
    BegenmeID INT PRIMARY KEY IDENTITY(1,1),
    VideoID INT FOREIGN KEY REFERENCES Video(VideoID),
    BegenenTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    BegenenID INT NOT NULL,
    BegenmeTarihi DATETIME DEFAULT GETDATE()
)

-- Izlenme Tablosu
CREATE TABLE Izlenme (
    IzlenmeID INT PRIMARY KEY IDENTITY(1,1),
    VideoID INT FOREIGN KEY REFERENCES Video(VideoID),
    IzleyenTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    IzleyenID INT NOT NULL,
    IzlenmeTarihi DATETIME DEFAULT GETDATE()
)

-- DersPlan Tablosu
CREATE TABLE DersPlan (
    DersPlanID INT PRIMARY KEY IDENTITY(1,1),
    DersID INT FOREIGN KEY REFERENCES Ders(DersID),
    OgretmenID INT FOREIGN KEY REFERENCES Ogretmen(OgretmenID),
    PlanBaslik NVARCHAR(200) NOT NULL,
    PlanIcerik NVARCHAR(MAX),
    OlusturmaTarihi DATETIME DEFAULT GETDATE(),
    GuncellemeTarihi DATETIME
)

-- Mesaj Tablosu
CREATE TABLE Mesaj (
    MesajID INT PRIMARY KEY IDENTITY(1,1),
    GonderenTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    GonderenID INT NOT NULL,
    AliciTip NVARCHAR(20) NOT NULL, -- 'Admin', 'Ogretmen' veya 'Ogrenci'
    AliciID INT NOT NULL,
    MesajIcerik NVARCHAR(1000) NOT NULL,
    GondermeTarihi DATETIME DEFAULT GETDATE(),
    OkunduMu BIT DEFAULT 0
)

-- Admin verileri
INSERT INTO Admin (KullaniciAdi, Sifre, Ad, Soyad, Email) VALUES
('admin1', 'hash123', 'Ahmet', 'Yılmaz', 'ahmet.yilmaz@okul.com'),
('admin2', 'hash124', 'Ayşe', 'Demir', 'ayse.demir@okul.com');

-- Ogretmen verileri
INSERT INTO Ogretmen (KullaniciAdi, Sifre, Ad, Soyad, Email, Brans) VALUES
('ogretmen1', 'hash125', 'Mehmet', 'Kaya', 'mehmet.kaya@okul.com', 'Matematik'),
('ogretmen2', 'hash126', 'Zeynep', 'Şahin', 'zeynep.sahin@okul.com', 'Fizik'),
('ogretmen3', 'hash127', 'Ali', 'Çelik', 'ali.celik@okul.com', 'Kimya');

-- Ogrenci verileri
INSERT INTO Ogrenci (KullaniciAdi, Sifre, Ad, Soyad, Email) VALUES
('ogrenci1', 'hash128', 'Can', 'Öztürk', 'can.ozturk@ogrenci.com'),
('ogrenci2', 'hash129', 'Elif', 'Yıldız', 'elif.yildiz@ogrenci.com'),
('ogrenci3', 'hash130', 'Deniz', 'Aydın', 'deniz.aydin@ogrenci.com');

-- Sinif verileri
INSERT INTO Sinif (SinifAdi, Aciklama) VALUES
('9-A', 'Dokuzuncu Sınıf A Şubesi'),
('10-B', 'Onuncu Sınıf B Şubesi'),
('11-A', 'On Birinci Sınıf A Şubesi');

-- Ders verileri
INSERT INTO Ders (DersAdi, SinifID, Aciklama) VALUES
('Matematik', 1, '9. Sınıf Matematik Dersi'),
('Fizik', 2, '10. Sınıf Fizik Dersi'),
('Kimya', 3, '11. Sınıf Kimya Dersi');

-- Unite verileri
INSERT INTO Unite (DersID, UniteAdi, UniteNo, Aciklama) VALUES
(1, 'Kümeler', 1, 'Matematik Kümeler Ünitesi'),
(1, 'Fonksiyonlar', 2, 'Matematik Fonksiyonlar Ünitesi'),
(2, 'Kuvvet ve Hareket', 1, 'Fizik Kuvvet ve Hareket Ünitesi');

-- Konu verileri
INSERT INTO Konu (UniteID, KonuAdi, KonuNo, Aciklama) VALUES
(1, 'Kümelerde Temel Kavramlar', 1, 'Küme Kavramı ve Gösterimi'),
(1, 'Kümelerde İşlemler', 2, 'Birleşim, Kesişim ve Fark İşlemleri'),
(2, 'Fonksiyon Kavramı', 1, 'Fonksiyon Tanımı ve Çeşitleri');

-- Video verileri
INSERT INTO Video (Baslik, VideoURL, KonuID, YukleyenTip, YukleyenID, Aciklama) VALUES
('Kümelere Giriş', 'https://video1.mp4', 1, 'Ogretmen', 1, 'Kümelere Giriş Videosu'),
('Fonksiyonlar', 'https://video2.mp4', 3, 'Admin', 1, 'Fonksiyonlar Konu Anlatımı'),
('Kümeler Alıştırma', 'https://video3.mp4', 2, 'Ogrenci', 1, 'Kümeler Konu Tekrarı'),
('Küme Problemleri Çözümü', 'https://video4.mp4', 1, 'Admin', 1, 'Admin tarafından hazırlanan örnek soru çözümleri'),
('Fonksiyonlarda Özel Durumlar', 'https://video5.mp4', 3, 'Admin', 2, 'Özel fonksiyon türleri ve özellikleri'),
('Arkadaşlar İçin Konu Özeti', 'https://video6.mp4', 2, 'Ogrenci', 2, 'Arkadaşım Elif tarafından hazırlanan özet video'),
('Sınav Öncesi Tekrar', 'https://video7.mp4', 1, 'Ogrenci', 3, 'Deniz''in sınav tekrar videosu');

-- Yorum verileri
INSERT INTO Yorum (VideoID, YorumYapanTip, YorumYapanID, YorumMetni) VALUES
(1, 'Ogrenci', 1, 'Çok faydalı bir video olmuş, teşekkürler'),
(1, 'Ogretmen', 2, 'Güzel bir anlatım örneği'),
(2, 'Ogrenci', 3, 'Biraz daha detaylı anlatabilir misiniz?'),
(4, 'Ogrenci', 2, 'Admin hocam ellerinize sağlık, çok açıklayıcı olmuş'),
(6, 'Ogretmen', 1, 'Elif, harika bir özet olmuş, arkadaşlarına çok yardımcı olacaktır'),
(7, 'Ogrenci', 1, 'Deniz teşekkürler, tam ihtiyacım olan tekrar videosuydu');

-- Begenme verileri
INSERT INTO Begenme (VideoID, BegenenTip, BegenenID) VALUES
(1, 'Ogrenci', 1),
(1, 'Ogrenci', 2),
(2, 'Ogretmen', 1),
(4, 'Ogrenci', 3),
(6, 'Ogretmen', 2),
(6, 'Ogrenci', 1),
(7, 'Admin', 1);

-- Izlenme verileri
INSERT INTO Izlenme (VideoID, IzleyenTip, IzleyenID) VALUES
(1, 'Ogrenci', 1),
(1, 'Ogrenci', 2),
(1, 'Ogretmen', 1),
(2, 'Ogrenci', 3),
(4, 'Ogrenci', 2),
(4, 'Ogrenci', 3),
(6, 'Ogretmen', 2),
(6, 'Ogrenci', 1),
(7, 'Admin', 1),
(7, 'Ogrenci', 2);

-- DersPlan verileri
INSERT INTO DersPlan (DersID, OgretmenID, PlanBaslik, PlanIcerik) VALUES
(1, 1, 'Kümeler Ders Planı', 'Kümeler ünitesi 4 haftalık ders planı...'),
(2, 2, 'Fizik Dönem Planı', 'Fizik dersi dönemlik plan içeriği...');

-- Mesaj verileri
INSERT INTO Mesaj (GonderenTip, GonderenID, AliciTip, AliciID, MesajIcerik) VALUES
('Ogrenci', 1, 'Ogretmen', 1, 'Hocam ödev hakkında sorum vardı'),
('Ogretmen', 1, 'Ogrenci', 1, 'Tabii ki sorabilirsin'),
('Admin', 1, 'Ogretmen', 2, 'Yarınki toplantıyı hatırlatırım'); 