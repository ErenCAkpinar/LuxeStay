# LuxeStay Demo Checklist

## 1. Kayıt ve giriş
- [x] Yeni kullanıcı `Sign Up` formundan oluşturuluyor.
- [x] Backend terminalinde `SIGNUP_POST` logu ile gelen POST verisi gösteriliyor.
- [x] Kullanıcı Django `auth_user` tablosuna hashlenmiş şifreyle yazılıyor.
- [x] Kullanıcı giriş yaptıktan sonra dashboard ekranına yönleniyor.

## 2. Otel arama ve filtreleme
- [x] Ana sayfadaki arama formu `/api/hotels/` endpointine istek atıyor.
- [x] Network sekmesinde REST API isteği ve dönen JSON gösterilebiliyor.
- [x] Backend terminalinde `API_HOTEL_SEARCH` ve `HOTEL_SEARCH` logları görünüyor.
- [x] `/hotels/` sayfası veritabanındaki otelleri lokasyon/misafir bilgisine göre filtreliyor.

## 3. Rezervasyon ve ödeme
- [x] Otel detayından checkout akışına geçiliyor.
- [x] Misafir bilgileri session üzerinden ödeme adımına taşınıyor.
- [x] Kredi kartı alanları backend tarafında format ve tarih kontrolünden geçiyor.
- [x] Rezervasyon oluşunca 9 haneli benzersiz booking ID veritabanına yazılıyor.
- [x] Rezervasyon sonrası ilgili otelin `rooms_left` değeri 1 azalıyor.
- [x] Backend terminalinde `BOOKING_CREATE before_stock` ve `BOOKING_CREATE saved` logları gösteriliyor.

## 4. Dashboard ve My Bookings
- [x] Kullanıcı dashboard sayfaları gerçek veritabanı kayıtlarını okuyor.
- [x] `My Bookings` hem giriş yapan kullanıcıya bağlı hem de aynı e-posta ile yapılan rezervasyonları gösteriyor.
- [x] Booking sayfasında cache kapatıldı; yeni rezervasyon sayfa yenilenince görünür.
- [x] İptal edilen rezervasyonlar kırmızı `CANCELLED` etiketiyle gösteriliyor.

## 5. Admin paneli
- [x] Demo admin kullanıcısı: `admin@luxestay.com` / `AdminPass123!`
- [x] Admin panelinden rezervasyon durumu `Cancelled` yapılabiliyor.
- [x] Durum değişikliği veritabanına yazılıyor.
- [x] Admin iptalinde oda stoğu geri artırılıyor.
- [x] Backend terminalinde `ADMIN_BOOKING_STATUS_CHANGE` logu gösteriliyor.

## Demo ekran düzeni
- [ ] Sol tarafta LuxeStay web uygulaması açık olsun.
- [ ] Sağ tarafta IDE terminali ve SQLite görüntüleyici açık olsun.
- [ ] Tarayıcı Network sekmesi `/api/hotels/` isteği için hazır olsun.
- [ ] Admin paneli `/admin/` ayrı sekmede açık olsun.
