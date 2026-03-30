# Kamienicznik / System do rozliczania najmu

## Opis ogólny (PL)

Aplikacja służy do zarządzania najmem mieszkań i rozliczania mediów na podstawie rzeczywistego zużycia. Jej celem jest maksymalne uproszczenie pracy właściciela/zarządcy kilku lokali, bez używania Excela i ręcznego liczenia.

### Główne możliwości

- **Zarządzanie mieszkaniami**
  - Rejestr lokali z adresem i opisem.
  - Flagi, jakie media są dostępne w danym lokalu (woda, prąd, gaz, śmieci, ogrzewanie itp.).
  - Aktywowanie/dezaktywowanie lokali bez usuwania historii.

- **Najemcy i umowy**
  - Przypisywanie najemców do konkretnych lokali.
  - Podgląd historii najmu i rozliczeń dla danego mieszkania.

- **Liczniki i odczyty**
  - Rejestr liczników (woda, prąd, gaz) dla każdego lokalu.
  - Wprowadzanie odczytów liczników, z możliwością dodania zdjęcia odczytu.
  - Oznaczanie zdjęć liczników jako zweryfikowane lub wymagające uwagi.

- **Stawki za media**
  - Definiowanie stawek dla różnych mediów (woda, śmieci, ogrzewanie, prąd – składowe, gaz – składowe, czynsz do wspólnoty).
  - Możliwość ustawienia **globalnej stawki** (dla wszystkich lokali) lub **indywidualnej stawki** przypisanej do konkretnego mieszkania.
  - Historia zmian stawek z datami obowiązywania.

- **Rozliczenia okresowe**
  - Tworzenie okresów rozliczeniowych dla każdego lokalu (np. miesiąc).
  - Automatyczne obliczanie kosztów mediów na podstawie:
    - zużycia z liczników,
    - aktualnych stawek (globalnych lub przypisanych do lokalu),
    - składowych cen prądu i gazu (sprzedaż, dystrybucja, VAT itp.).
  - Generowanie pozycji rozliczenia (woda, prąd, gaz, śmieci, ogrzewanie, czynsz wspólnoty).
  - Podgląd szczegółów wyliczeń w opisie każdej pozycji.

- **Płatności i saldo**
  - Rejestrowanie wpłat od najemców.
  - Powiązanie płatności z okresami rozliczeniowymi.
  - Podgląd aktualnego salda i zaległości.

- **Panel administracyjny**
  - Logowanie do panelu administracyjnego jako właściciel/administrator.
  - Reset hasła z poziomu aplikacji (bez konieczności posiadania prawdziwej skrzynki e‑mail).
  - Widok „kokpitu” z podsumowaniem: zaległe rozliczenia, ostatnie płatności, liczba zdjęć liczników do weryfikacji.

Aplikacja jest zaprojektowana z myślą o jednym właścicielu/zarządcy posiadającym kilka mieszkań w różnych lokalizacjach. Kluczowy nacisk położono na czytelność rozliczeń, elastyczność stawek oraz możliwość późniejszego rozbudowania o dodatkowe media lub typy opłat.

***

## General description (EN)

This application is designed to manage rental apartments and calculate utility charges based on actual consumption. The goal is to simplify the daily work of a small landlord/property manager and get rid of spreadsheets and manual calculations.

### Key features

- **Apartments management**
  - Register apartments with address and description.
  - Flags indicating which utilities are available for a given apartment (water, electricity, gas, trash, heating, etc.).
  - Activate/deactivate apartments without losing their history.

- **Tenants and tenancy**
  - Assign tenants to specific apartments.
  - View rental and billing history for each apartment.

- **Meters and readings**
  - Register utility meters (water, electricity, gas) per apartment.
  - Enter meter readings, optionally with meter photos.
  - Mark meter photos as verified or requiring attention.

- **Utility rates**
  - Define rates for different utilities (water, trash, heating, electricity components, gas components, community fee).
  - Support **global rates** (used for all apartments) and **per‑apartment rates** assigned to a specific unit.
  - Full history of rate changes with validity dates.

- **Billing periods**
  - Create billing periods per apartment (e.g. monthly).
  - Automatically calculate utility costs based on:
    - meter consumption,
    - current rates (global or apartment‑specific),
    - detailed electricity and gas components (energy sale, distribution, VAT, etc.).
  - Generate billing line items (water, electricity, gas, trash, heating, community fee).
  - Show detailed calculation breakdown in each billing line description.

- **Payments and balance**
  - Record tenant payments.
  - Link payments to billing periods.
  - View current balance and outstanding debt.

- **Admin panel**
  - Log in as owner/administrator to manage the system.
  - Password reset flow handled inside the app (no real e‑mail inbox required).
  - Dashboard with an overview: overdue bills, recent payments, number of meter photos waiting for review.

The application is built for a single landlord/property manager with several apartments in different locations. It focuses on clear billing, flexible utility rates, and the ability to extend the system with new utility types or fees in the future.
