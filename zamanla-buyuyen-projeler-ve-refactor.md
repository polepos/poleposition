# Zamanla Büyüyen Projeler ve Kaçınılmaz Refactor: 1948 Satırlık Bir Dosyayı Nasıl Böldük

## Kimse "bu dosya 2000 satır olsun" diye karar vermedi

Bir gün bir dosyayı açtım: `project_checker.py`, 1948 satır. Tek bir sınıf değil,
tek bir dev fonksiyon da değil. Onlarca küçük fonksiyon, hepsi makul, hepsi
gerekli. Hiçbiri tek başına "kötü kod" değildi. Ama dosyanın tamamı, açtığın
anda hangi bölümde olduğunu unutturan, arama yapmadan gezinemediğin bir
labirente dönüşmüştü.

İlginç olan şu: kimse oturup "bu dosya 2000 satır olsun" demedi. Dosya, aylar
içinde, her biri tek başına mantıklı küçük eklemelerle oraya geldi. Bir komut
eklendi, bir kontrol katmanı geldi, bir entegrasyon doğrulaması yazıldı, derken
proje "lifecycle CLI" oldu ve checker bütün bu yaşam döngüsünü tek dosyada
doğrulamaya başladı.

Bu yazı, tam olarak bunun hikayesi: kodun nasıl sessizce biriktiği, ne zaman
gerçekten bir soruna dönüştüğü ve davranışı hiç bozmadan nasıl
toparlanabileceği.

## Kod birikerek büyür, ve bu çoğu zaman normaldir

Yeşil alan projesinin ilk günü her şey temizdir. Sonra ürün yaşamaya başlar.
Gerçek projelerde büyüme şöyle olur:

- Yeni bir özellik geldi, en yakın "uygun" dosyaya bir fonksiyon eklendi.
- Bir edge case çıktı, mevcut fonksiyona bir `if` daha kondu.
- "Şimdilik buraya koyayım, sonra taşırım" denildi (ve taşınmadı).
- Test geçiyordu, review temizdi, merge edildi.

Her adım tek başına doğruydu. Sorun, adımların **toplamında** birikiyor. Buna
yazılımda genelde "yavaş yavaş ısınan su" denir: tek tek hiçbir commit alarm
vermez, ama bir noktada dosya artık zihinsel olarak tek seferde kavranamaz hale
gelir.

Önemli olan şu: birikerek büyümek bir başarısızlık değil. Bir projenin
büyümesi, kullanıldığının kanıtı. Asıl mesele, büyümenin işaretlerini görüp
doğru anda yapıyı toparlamak.

## Ne zaman "büyük dosya" gerçekten bir soruna dönüşür

Satır sayısı tek başına bir kriter değil. Bir dosyanın refactor istediğini şu
sinyallerden anlarsın:

1. **Gezinme maliyeti.** "Şu kontrolü nerede yapıyorduk?" sorusuna ancak arama
   yaparak cevap verebiliyorsan, dosya artık bir harita gerektiriyor demektir.
2. **Karışan sorumluluklar.** Aynı dosyada hem dosya okuma helper'ları, hem iş
   kuralları, hem hata mesajı katalogu, hem orkestrasyon varsa, dosya birden çok
   sebeple değişiyor demektir (Single Responsibility'nin ihlali).
3. **Değişiklik korkusu.** Küçük bir düzeltme için dosyayı açtığında "acaba
   alakasız bir yeri bozar mıyım" diye tereddüt ediyorsan, bilişsel yük çok
   yükselmiştir.
4. **Review'ın zorlaşması.** Diff'ler dosyanın her yerine dağılıyor, reviewer
   bağlamı tutamıyorsa.
5. **Test edilebilirliğin azalması.** Tek bir parçayı izole test etmek için
   koca dosyayı import etmek gerekiyorsa.

Bizim `project_checker.py` bu sinyallerin hepsini veriyordu: proje kimliği,
üretilen yapı, Alembic, managed marker'lar, modül wiring, orphan temizliği,
auth workflow, entegrasyon doğrulamaları, bir de PPCHK hata kodu katalogu. Dokuz
ayrı sorumluluk, tek dosyada.

## İlke: boyuta göre değil, sorumluluğa göre böl

Refactor'a başlarken en sık yapılan hata, "dosya büyük, ikiye bölelim" demek.
Bu işe yaramaz: 1948 satırı 974 + 974 yapmak, sadece sorunu iki dosyaya
dağıtır.

Asıl kazanç, **sorumluluğa göre** ayırmaktan gelir. Soru "dosya kaç satır"
değil, "bu dosya kaç farklı sebeple değişiyor". Her bağımsız sebep, kendi
modülünü hak eder.

Bizim ulaştığımız hedef yapı şuydu: ince bir **facade** (sadece çağıran, yöneten
katman) artı sorumluluğa göre gruplanmış kardeş modüller:

```
services/project_checker/
  __init__.py      # facade: orchestrator + public API
  constants.py     # sabitler
  io.py            # dosya/parse/anahtar helper'ları
  report.py        # sonuç tipleri + hata/remediation katalogu
  discovery.py     # proje keşfi + veritabanı modu
  core.py          # kimlik, manifest, yapı, alembic, marker
  lifecycle.py     # modül wiring + orphan kontrolleri
  auth.py          # auth workflow kontrolleri
  deps.py          # paylaşılan pyproject bağımlılık parse
  integration.py   # entegrasyon wiring kontrolleri
```

Facade artık sadece şunu yapıyor: hangi kontrolü hangi sırayla çağıracağını
bilmek. 1948 satır, 116 satırlık bir orkestratöre indi. Geri kalan her şey, tek
sorumluluğu olan, tek başına okunabilen modüllerde.

## Güvenli yöntem: facade + adım adım çıkarma

Davranışı bozmadan büyük bir dosyayı bölmenin anahtarı, işi tek seferde değil,
küçük ve doğrulanabilir adımlarla yapmak. Bizim izlediğimiz akış:

1. **Baseline al.** Tüm testleri çalıştır, yeşil olduğunu gör, dosyanın dışarıya
   verdiği import yüzeyini (hangi dosya neyi import ediyor) bir kenara not et.
2. **Yapraktan köke doğru çıkar.** Önce hiçbir şeye bağımlı olmayan parçaları
   (sabitler, IO helper'ları), sonra onları kullanan kontrol katmanlarını, en
   sona orkestratörü.
3. **Her adımda tek bir cohesive grup taşı**, sonra hemen `pytest` ve linter
   çalıştır. Yeşilse commit et.
4. **Her adım ayrı commit.** Böylece review eden kişi her taşımayı tek tek
   görebilir, bir şey ters giderse hangi adımda olduğu bellidir.

Biz 1948 satırı dokuz commit'te, her biri yeşil kalacak şekilde böldük.
Bağımlılık yönünü tek taraflı tuttuk (döngü yok):

```
constants, io, report, deps        (yaprak: kimseyi import etmez)
        |
discovery, core, lifecycle, auth   (yaprakları kullanır)
        |
integration                        (lifecycle'a bağımlı)
        |
__init__ (facade)                  (hepsini çağırır ve re-export eder)
```

## Dış yüzeyi koru: iyi refactor görünmezdir

Bir refactor'ın altın kuralı: dışarıdan bakan kimse fark etmemeli. Testler,
diğer modüller, çağıran kod aynen çalışmaya devam etmeli.

`project_checker`'ı bir dosyadan bir pakete çevirdik, ama `__init__.py`'yi
facade yaptığımız için import yolu değişmedi:

```python
# Bu satır, project_checker ister tek dosya, ister paket olsun, aynen calisir:
from pole_position.cli.services.project_checker import check_project
```

Python için `project_checker/__init__.py`, `project_checker.py` ile aynı noktalı
yola çözülür. Yani iç organizasyonu tamamen değiştirdik, dış API'ye hiç
dokunmadık.

İç modüllere taşınan ama dışarıdan hâlâ import edilen isimleri (sonuç tipleri,
bazı test-helper fonksiyonları) facade'den re-export ettik. Burada küçük bir
linter tuzağı var: re-export edilen ama o dosyada "kullanılmayan" import'lar
"unused import" uyarısı verir. Çözüm, `__all__` ile public yüzeyi açıkça
bildirmek:

```python
__all__ = [
    "check_project",
    "ProjectCheckResult",
    "describe_project_check_issue",
    # ... disaridan kullanilan diger isimler
]
```

`__all__`'daki isimler linter tarafından "kullanılmış" sayılır; hem F401
uyarısı susar, hem de modülün public sözleşmesi belgelenmiş olur.

## Yol boyunca düşülen tuzaklar (ve onları yakalayan güvenlik ağı)

Saf mekanik taşıma bile hatasız değildir. Bizim takıldıklarımız:

- **Eksik import.** Bir modülü taşırken `import re` veya
  `from ... import read_project_manifest` taşımayı unutmak çok kolay. Bunları
  iki katman yakaladı: linter'ın "tanımsız isim" kuralı (statik) ve testlerin
  `NameError`'ı (runtime). Bir keresinde linter, henüz hiçbir test çalışmadan
  eksik bir `Path` import'unu yakaladı ve CI'ı baştan kurtardı.
- **Dairesel bağımlılık.** Sonuç tipi (`ProjectCheckResult`) hata katalogunu
  çağırıyordu, hata katalogu da sonuç tipini. Çözüm: ikisini aynı cohesive
  modülde tutmak (zorla ayırmak yerine).
- **Paylaşılan helper'lar.** Hem auth hem entegrasyon, pyproject bağımlılık
  kontrolünü kullanıyordu. Bunu birinin içine gömmek yerine, ortak bir `deps`
  modülüne çıkardık. İki tüketici de oraya bağımlı, ama birbirlerine değil.

Buradaki en kritik nokta: **güvenlik ağı olmadan refactor yapma.** Bizim
ağımız 320'den fazla testti. Her adımda yeşil kalmaları, "davranışı bozmadan
taşıyorum" iddiasının tek geçerli kanıtıydı. Test yoksa, ilk iş refactor değil,
test yazmaktır.

## Ne zaman refactor etmemeli

Refactor bir amaç değil, araç. Şunlara dikkat:

- **Davranış değişikliğiyle karıştırma.** Refactor commit'i hiçbir davranışı
  değiştirmemeli. "Madem açtım, şu bug'ı da düzelteyim" deme; o ayrı bir commit
  (ve ayrı bir PR) olmalı. Karışırsa, bir sorun çıktığında sebebi izole
  edemezsin.
- **"Stabil ve dokunulmayan" kodu kovalama.** Yıllardır değişmeyen, kimseyi
  rahatsız etmeyen bir dosyayı sırf "büyük" diye bölmek, risk alıp karşılığını
  alamamaktır. Refactor'ı, aktif olarak üstünde çalıştığın ve acı çektiğin
  yerlere yatır.
- **Doğru anı seç.** Özellik teslimine bir gün kala büyük bir refactor'a
  girişme. Refactor'ın değeri zamanla gelir; aciliyetle yarışmamalı.

## Çıkarımlar

- Kod birikerek büyür ve bu, kullanılan bir ürünün doğal hali. Suçluluk değil,
  bakım meselesi.
- Refactor kararını satır sayısı değil, sorumluluk karışıklığı ve değişiklik
  korkusu verir.
- Boyuta göre değil, sorumluluğa göre böl. İnce bir facade, kalını birkaç
  cohesive modüle dağıt.
- Tek seferde değil, yapraktan köke, adım adım, her adımda yeşil testlerle
  ilerle. Her adım ayrı commit.
- İyi refactor görünmezdir: dış import yüzeyini koru, davranışı değiştirme.
- Test güvenlik ağın; yoksa önce onu kur.

1948 satır kötü bir mühendisin işi değildi. Sadece, kimsenin "şimdi durup
toparlayalım" demediği bir büyümenin sonucuydu. İyi haber şu: doğru yöntemle,
o "şimdi" her zaman bulunabilir, ve hiçbir kullanıcı farkı anlamadan kod yeniden
nefes alabilir.
