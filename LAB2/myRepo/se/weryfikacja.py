"""Weryfikacja bazy wiedzy (odpowiednik programu Cake z pakietu SPHINX).
Uruchom: python se/weryfikacja.py wiedza/kawa_z_bledami.json
"""
import sys
from pathlib import Path

from silnik import OPERATORY, wczytaj_baze


def weryfikuj(baza):
    """Zwraca listę (poziom, komunikat); poziom to 'BŁĄD' albo 'UWAGA'."""
    raport = []
    atrybuty = baza["atrybuty"]
    reguly = baza["reguly"]

    # Test 1 (gotowy): powtórzone identyfikatory reguł
    ids = [r["id"] for r in reguly]
    for id_ in sorted({i for i in ids if ids.count(i) > 1}):
        raport.append(("BŁĄD", f"Powtórzony identyfikator reguły {id_}"))

    # Test 2 (gotowy): niezadeklarowane atrybuty i nieznane operatory w warunkach
    for r in reguly:
        for atr, op, wart in r["jesli"]:
            if atr not in atrybuty:
                raport.append(("BŁĄD", f"{r['id']}: niezadeklarowany atrybut '{atr}'"))
            if op not in OPERATORY:
                raport.append(("BŁĄD", f"{r['id']}: nieznany operator '{op}'"))

    # Test 3: wartości spoza dziedziny — dla atrybutów z listą "wartosci"
    #         sprawdź warunki z operatorem == lub != (BŁĄD).
    for r in reguly:
        for atr, op, wart in r["jesli"]:
            if atr in atrybuty and op in ("==", "!="):
                opis = atrybuty[atr]
                if "wartosci" in opis and wart not in opis["wartosci"]:
                    raport.append((
                        "BŁĄD",
                        f"{r['id']}: wartość {wart!r} spoza dziedziny atrybutu '{atr}'",
                    ))

    # Test 4: nieużywane atrybuty wejściowe (typ inny niż "wniosek", nieobecne w żadnym warunku)
    #         oraz nieużywane wartości atrybutów typu "wybor" (UWAGA).
    w_uzytych_warunkach = {atr for r in reguly for atr, _, _ in r["jesli"]}
    for nazwa, opis in atrybuty.items():
        if opis.get("typ") != "wniosek" and nazwa not in w_uzytych_warunkach:
            raport.append(("UWAGA", f"Atrybut wejściowy '{nazwa}' nie występuje w żadnym warunku reguły."))
        if opis.get("typ") == "wybor":
            wartosci_uzyte = {
                wart for r in reguly for a, op, wart in r["jesli"]
                if a == nazwa and op in ("==", "!=")
            }
            for wartosc in opis.get("wartosci", []):
                if wartosc not in wartosci_uzyte:
                    raport.append((
                        "UWAGA",
                        f"Wartość {wartosc!r} atrybutu '{nazwa}' nie jest używana w żadnym warunku.",
                    ))

    # Test 5: warunek niemożliwy do spełnienia — warunek atr == wart, gdzie atr jest typu "wniosek",
    #         a żadna reguła nie ma wniosku ["atr", "wart"] (BŁĄD).
    wnioski = {}
    for r in reguly:
        atrybut, wartosc = r["to"]
        wnioski.setdefault(atrybut, set()).add(wartosc)
    for r in reguly:
        for atr, op, wart in r["jesli"]:
            if op == "==" and atr in atrybuty and atrybuty[atr].get("typ") == "wniosek":
                if wart not in wnioski.get(atr, set()):
                    raport.append((
                        "BŁĄD",
                        f"{r['id']}: warunek {atr} == {wart!r} jest niemożliwy do spełnienia "
                        f"(żadna reguła nie wnosi {atr} = {wart!r})",
                    ))

    # Test 6: porównaj każdą parę reguł (warunki jako zbiory krotek)
    #   - te same warunki i ten sam wniosek       -> duplikat (UWAGA)
    #   - te same warunki, inna wartość wniosku   -> sprzeczność (BŁĄD)
    #   - ten sam wniosek, warunki A ⊂ warunki B  -> B jest pochłaniana przez A (UWAGA)
    zbiory_warunkow = [{tuple(w) for w in r["jesli"]} for r in reguly]
    for i in range(len(reguly)):
        for j in range(i + 1, len(reguly)):
            wi, wj = zbiory_warunkow[i], zbiory_warunkow[j]
            ri, rj = reguly[i], reguly[j]
            ci, cj = tuple(ri["to"]), tuple(rj["to"])
            if wi == wj:
                if ci == cj:
                    raport.append((
                        "UWAGA",
                        f"{rj['id']} jest duplikatem {ri['id']} (te same warunki i ten sam wniosek)",
                    ))
                else:
                    raport.append((
                        "BŁĄD",
                        f"{ri['id']} i {rj['id']} są sprzeczne (te same warunki, inny wniosek)",
                    ))
            elif ci == cj:
                if wi < wj:
                    raport.append((
                        "UWAGA",
                        f"{rj['id']} jest pochłaniana przez {ri['id']} "
                        f"(ten sam wniosek, warunki {ri['id']} ⊂ {rj['id']})",
                    ))
                elif wj < wi:
                    raport.append((
                        "UWAGA",
                        f"{ri['id']} jest pochłaniana przez {rj['id']} "
                        f"(ten sam wniosek, warunki {rj['id']} ⊂ {ri['id']})",
                    ))

    # Test 7: cel główny baza["cel"] musi być wnioskiem co najmniej jednej reguły (BŁĄD).
    cel = baza.get("cel")
    if cel is not None:
        atrybuty_wniosku = {r["to"][0] for r in reguly}
        if cel not in atrybuty_wniosku:
            raport.append(("BŁĄD", f"Cel '{cel}' nie jest wnioskiem żadnej reguły."))

    return raport


if __name__ == "__main__":
    plik = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "wiedza" / "kawa_z_bledami.json"
    wyniki = weryfikuj(wczytaj_baze(plik))
    if not wyniki:
        print("Baza wiedzy nie zawiera wykrytych problemów.")
    for poziom, komunikat in wyniki:
        print(f"[{poziom}] {komunikat}")
    print(f"\nZnaleziono: {len(wyniki)} błędów w bazie wiedzy {plik}.")
