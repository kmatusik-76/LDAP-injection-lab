# Zadania

Aplikacja startuje w trybie **PODATNY** (czerwony baner). W tym trybie wykonaj
oba zadania. Potem przełącz na **BEZPIECZNY** (zielony baner) i sprawdź, że te
same ataki już nie działają — to jest cała lekcja.

Na każdym ekranie pod formularzem widać **filtr LDAP wysłany do serwera**.
Obserwuj, jak zmienia się po wpisaniu różnych rzeczy — to najlepsza podpowiedź.

---

## Zadanie 1

**Cel:** zalogować się jako użytkownik `admin`, nie znając jego hasła.

Ekran: **Logowanie**.

**Dowód wykonania:** po zalogowaniu zobaczysz atrybut `description` konta admina —
zawiera flagę.

## Zadanie 2

**Cel:** wyświetlić pracowników oznaczonych jako niepubliczni (`restricted`),
których zwykłe wyszukiwanie nie pokazuje (m.in. zarząd i oficer bezpieczeństwa).

Ekran: **Wyszukiwarka pracowników**.

Co warto wiedzieć:
- Wyszukiwarka to „książka adresowa" — normalnie wpisujesz fragment nazwiska.
- W trybie podatnym Twój tekst trafia wprost do filtra i **nie ma** żadnego
  ograniczenia „tylko publiczni".
- Spróbuj wpisać coś, co pasuje do *wszystkich* wpisów naraz.

**Dowód wykonania:** wśród wyników pojawi się konto `restricted` z flagą
`FLAG{...}` w kolumnie `description`, a także prywatne numery telefonów, które
nie powinny być widoczne.

---

## Po wykonaniu — przełącz na BEZPIECZNY

Kliknij **„Przelacz na BEZPIECZNY"** w banerze i powtórz oba ataki. Zwróć uwagę:
- jak zmienia się filtr LDAP (pojawia się `\2a` zamiast `*`),
- dlaczego logowanie teraz wymaga prawdziwego hasła,
- dlaczego `restricted` znika z wyników.