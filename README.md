
<div align="right">
  <a href="README.en.md">
    <img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge" alt="Read in English">
  </a>
</div>

 ![LibreOffice Calc Çoklu Belge Arama Ekran Görüntüsü](https://raw.githubusercontent.com/erdincyz/gorseller/refs/heads/main/_cesitli/libre_calc_coklu_ara_ekran_goruntusu.jpg)


# LibreOffice Calc Çoklu Belge Arama Makrosu

Bu proje, açık olan tüm LibreOffice Calc (Excel) belgelerinde aynı anda arama yapmanızı sağlayan Python tabanlı bir makrodur. 

LibreOffice'in standart arama işlevinden farklı olarak, tüm sekmeleri ve dosyaları tek bir ekranda tarar, sistemi dondurmaz ve sonuçları listeler.

## Özellikler

* **Çoklu Tarama:** Sadece aktif sayfada veya açık olan tüm LibreOffice dosyalarında arama yapabilme.
* **Gelişmiş Arama Seçenekleri:**
  * **Bulanık (Fuzzy) Arama:** Kelimeyi yanlış yazsanız bile en yakın sonuçları bulur.
  * **Regex:** Düzenli ifadeler ile karmaşık desen aramaları.
  * **Tam Kelime ve Büyük/Küçük Harf Duyarlılığı.**
* **Hızlı Erişim:** Çıkan listedeki sonuca çift tıkladığınızda o dosyadaki ilgili hücreye anında gider.
* **Dışa Aktarma:** Bulunan sonuçları tek tıkla `.csv` formatında kaydedebilirsiniz.
* **Yüksek Performans ve Güvenlik:** Arama işlemi arka planda (Worker Thread) yapılır. Yüz binlerce satırlık dosyalarda bile LibreOffice donmaz veya çökmez. RAM tüketimini engellemek için bellek koruması mevcuttur.

---

## Kurulum

LibreOffice, Python makrolarını işletim sistemine göre belirli bir klasörde arar. Kurulum için `coklu_belgede_ara.py` dosyasını indirip, işletim sisteminize uygun olan klasöre kopyalamanız yeterlidir.

**Önemli:** Eğer belirtilen yollarda `Scripts` ve `python` klasörleri yoksa, bu klasörleri kendiniz oluşturmalısınız (büyük/küçük harflere dikkat edin).

### 🪟 Windows İçin Kurulum
1. `coklu_belgede_ara.py` dosyasını indirin.
2. Klavyenizden `Windows + R` tuşlarına basarak "Çalıştır" penceresini açın.
3. Şu yolu kopyalayıp yapıştırın ve Enter'a basın:
   `%APPDATA%\LibreOffice\4\user\Scripts\`
4. Açılan yerde `python` adında bir klasör yoksa oluşturun.
5. İndirdiğiniz `.py` dosyasını bu `python` klasörünün içine kopyalayın.
   *(Tam yol şuna benzemelidir: `C:\Users\KullaniciAdi\AppData\Roaming\LibreOffice\4\user\Scripts\python\coklu_belgede_ara.py`)*

### 🐧 Linux İçin Kurulum
Linux dağıtımlarında arayüz penceresi için `tkinter` paketinin sistemde kurulu olması gerekir.
1. Terminali açın ve tkinter'ı kurun:
   * Debian/Ubuntu tabanlı sistemlerde: `sudo apt-get install python3-tk`
   * Fedora/RHEL tabanlı sistemlerde: `sudo dnf install python3-tkinter`
2. Dosya yöneticisini açın ve `Gizli Dosyaları Göster` seçeneğini aktif edin (Genelde `Ctrl + H`).
3. Şu yola gidin: `~/.config/libreoffice/4/user/Scripts/python/`
   *(Klasörler yoksa terminalden şu komutla oluşturabilirsiniz: `mkdir -p ~/.config/libreoffice/4/user/Scripts/python`)*
4. İndirdiğiniz `.py` dosyasını bu klasörün içine kopyalayın.

### 🍎 macOS İçin Kurulum
1. `coklu_belgede_ara.py` dosyasını indirin.
2. Finder'ı açın, üst menüden **Git (Go)** seçeneğine tıklayın.
3. Klavyenizdeki `Option (Alt)` tuşuna basılı tutun. Menüde **Kütüphane (Library)** seçeneği belirecektir, ona tıklayın.
4. Şu yola gidin: `Application Support/LibreOffice/4/user/Scripts/python/`
   *(Eğer `Scripts` ve `python` klasörleri yoksa yeni klasör oluşturarak isimlerini verin).*
5. İndirdiğiniz dosyayı buraya bırakın.

---

## ⚙️ Menüye Buton Ekleme

Dosyayı koyduktan sonra LibreOffice'in bunu görmesi ve kolayca çalıştırmanız için bir buton ekleyelim.

1.  **LibreOffice Calc**'ı tamamen kapatıp yeniden açın.
2.  Menüden **Araçlar (Tools) > Özelleştir (Customize)** yolunu izleyin.
3.  **Menüler (Menus)** sekmesine gelin.
4.  Arama kutusuna veya Kategori kısmına bakın:
    *   **LibreOffice Makroları** > **Makrolarım** > **coklu_belgede_ara** yolunu izleyin.
    *   Orada `CokluAramaMacro` göreceksiniz.
5.  Sağ taraftaki ok (`->`) ile bunu menüye ekleyin.
6.  İsterseniz eklediğiniz öğeye sağ tıklayıp adını **"Çoklu Ara"** olarak değiştirin.

Artık menüdeki butona basarak çalıştırabilirsiniz!

---

## Teknik Notlar

* Makro, ayarlarınızı ve son arama geçmişinizi bilgisayarınızda `~/.multi_search_config.json` dosyasında tutar.
* Olası hatalar arayüzü çökertmemesi için `~/.multi_search.log` dosyasına kaydedilir. Sorun yaşarsanız bu dosyayı inceleyebilirsiniz.

