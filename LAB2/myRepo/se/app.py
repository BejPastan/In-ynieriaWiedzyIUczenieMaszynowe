"""Interfejs systemu ekspertowego — uzupełnione na spotkaniu 3. Uruchom: streamlit run app.py"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "se"))
from silnik import coto, wczytaj_baze, wnioskuj_w_przod, wyjasnij_jak, wnioskuj_wstecz
from weryfikacja import weryfikuj

PLIK_BAZY = Path(__file__).parent.parent / "wiedza" / "moja_dziedzina.json"
baza = wczytaj_baze(PLIK_BAZY)


st.set_page_config(page_title=baza["nazwa"])
st.title(baza["nazwa"])

with st.sidebar:
    st.header("Weryfikacja bazy wiedzy")
    raport = weryfikuj(baza)
    if not raport:
        st.success("Nie wykryto problemów.")
    for poziom, komunikat in raport:
        (st.error if poziom == "BŁĄD" else st.warning)(komunikat)

with st.form("konsultacja"):
    fakty = {}
    for nazwa, opis in baza["atrybuty"].items():
        if opis["typ"] == "liczba":
            lo, hi = opis.get("zakres", [-100, 100])
            fakty[nazwa] = st.slider(opis["pytanie"], lo, hi, (lo + hi) // 2)
        elif opis["typ"] == "wybor":
            fakty[nazwa] = st.radio(opis["pytanie"], opis["wartosci"])
    wyslano = st.form_submit_button("Doradź")

if wyslano:
    wynik, slad = wnioskuj_w_przod(baza, fakty)
    w_wynik = wnioskuj_wstecz(baza, baza["cel"], fakty, None )
    cel = baza["cel"]
    wartosc = wynik.get(cel)
    if wartosc is None:
        st.error(f"Nie znaleziono reguły, która pozwoliłaby określić wartość celu '{cel}'.")
    else:
        st.success(f"{cel}: {wartosc}")
        st.success(f"{cel}: {w_wynik}")
        st.info(coto(baza, slad))
    with st.expander("Jak do tego doszedłem?"):
        for krok in wyjasnij_jak(baza, slad):
            st.write(krok)
