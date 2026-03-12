import streamlit as st
import requests
from datetime import datetime
import plotly.express as px

# Konfiguracja strony
st.set_page_config(page_title="Faceit Tracker", page_icon="🎮", layout="wide")

BASE_URL = "https://open.faceit.com/data/v4"
GAME = "cs2"
# Twój klucz API wpisany na stałe
API_KEY = "e48abb41-5766-453c-b372-40bcac71b1fe"

# --- SYSTEM ZMIANY NICKÓW ---
if 'wybrany_gracz' not in st.session_state:
    st.session_state['wybrany_gracz'] = "mruwkojad13"

def ustaw_gracza(nick):
    st.session_state['wybrany_gracz'] = nick

# --- FUNKCJE API ---
def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }

def get_player_info(nickname, headers):
    url = f"{BASE_URL}/players"
    response = requests.get(url, headers=headers, params={"nickname": nickname})
    if response.status_code == 200:
        data = response.json()
        player_id = data.get("player_id")
        elo = data.get("games", {}).get("cs2", {}).get("faceit_elo", "Brak")
        avatar = data.get("avatar", "")
        return {"player_id": player_id, "elo": elo, "avatar": avatar}
    return None

def get_match_history(player_id, limit, headers):
    url = f"{BASE_URL}/players/{player_id}/history"
    params = {"game": GAME, "offset": 0, "limit": limit}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()["items"]
    return []

def get_match_stats(match_id, headers):
    url = f"{BASE_URL}/matches/{match_id}/stats"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def get_todays_wl(player_id, headers):
    midnight = datetime.combine(datetime.today(), datetime.min.time()).timestamp()
    matches = get_match_history(player_id, 20, headers)
    
    wins = 0
    losses = 0
    
    for match in matches:
        if match.get("finished_at", 0) >= midnight:
            match_id = match["match_id"]
            stats = get_match_stats(match_id, headers)
            if stats and "rounds" in stats:
                match_data = stats["rounds"][0]
                for team in match_data["teams"]:
                    for player in team["players"]:
                        if player["player_id"] == player_id:
                            result = player["player_stats"].get("Result", "0")
                            if result == "1":
                                wins += 1
                            else:
                                losses += 1
        else:
            break
            
    elo_change = (wins * 25) - (losses * 25)
    return wins, losses, elo_change

# --- GŁÓWNA LOGIKA ANALIZY ---
def analyze_data(matches, player_id, headers):
    total_kills, total_deaths, total_assists, total_headshots = 0, 0, 0, 0
    sum_kr, sum_adr = 0.0, 0.0
    matches_with_adr = 0
    valid_matches = 0

    categories = {
        "win_carried": 0, "win_avg": 0, "win_carried_by": 0,
        "loss_trolled": 0, "loss_avg": 0, "loss_my_fault": 0
    }

    progress_bar = st.progress(0)
    
    for i, match in enumerate(matches):
        match_id = match["match_id"]
        stats = get_match_stats(match_id, headers)
        
        if stats and "rounds" in stats:
            match_data = stats["rounds"][0]
            for team in match_data["teams"]:
                for player in team["players"]:
                    if player["player_id"] == player_id:
                        p_stats = player["player_stats"]
                        
                        total_kills += int(p_stats.get("Kills", 0))
                        total_deaths += int(p_stats.get("Deaths", 0))
                        total_assists += int(p_stats.get("Assists", 0))
                        total_headshots += int(p_stats.get("Headshots", 0))
                        
                        kr_str = p_stats.get("K/R Ratio", "0")
                        sum_kr += float(kr_str) if kr_str else 0.0
                        
                        adr_str = p_stats.get("ADR", "0")
                        current_adr = float(adr_str) if adr_str else 0.0
                        
                        result = p_stats.get("Result", "0")

                        if current_adr > 0:
                            sum_adr += current_adr
                            matches_with_adr += 1
                            
                            if result == "1":
                                if current_adr > 95: categories["win_carried"] += 1
                                elif 75 <= current_adr <= 95: categories["win_avg"] += 1
                                else: categories["win_carried_by"] += 1
                            else:
                                if current_adr > 90: categories["loss_trolled"] += 1
                                elif 70 <= current_adr <= 90: categories["loss_avg"] += 1
                                else: categories["loss_my_fault"] += 1
                        valid_matches += 1
        
        progress_bar.progress((i + 1) / len(matches))

    if valid_matches == 0:
        return None

    return {
        "valid_matches": valid_matches,
        "avg_kills": total_kills / valid_matches,
        "avg_deaths": total_deaths / valid_matches,
        "avg_assists": total_assists / valid_matches,
        "kd": total_kills / total_deaths if total_deaths > 0 else total_kills,
        "kr": sum_kr / valid_matches,
        "adr": sum_adr / matches_with_adr if matches_with_adr > 0 else 0.0,
        "hs_percent": (total_headshots / total_kills) * 100 if total_kills > 0 else 0.0,
        "categories": categories
    }

# --- INTERFEJS UŻYTKOWNIKA (UI) ---
st.title("ELO CHECKER v 1.0")
st.markdown("daj nick i powiedz co cie interesuje.")

# Pasek boczny (Sidebar) na ustawienia
with st.sidebar:
    st.header("⚙️ Ustawienia")
    # Pole tekstowe jest teraz podpięte pod klucz "wybrany_gracz"
    nick_input = st.text_input("nick", key="wybrany_gracz")
    zakres = st.radio("zakresik:", ["Ostatnie 10 meczy", "Ostatnie 30 meczy", "Dzisiejsze mecze"])
    odpal = st.button("jazda", use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### n00bki do elocheckingu")
    st.button("👷 inżynier latino final boss", on_click=ustaw_gracza, args=("mruwkojad13",), use_container_width=True)
    st.button("👶 małolat", on_click=ustaw_gracza, args=("nekuu--",), use_container_width=True)
    st.button("🧘‍♂️ low cortisol player", on_click=ustaw_gracza, args=("Jastrzebino",), use_container_width=True)
    st.button("🤬 high cortisol player", on_click=ustaw_gracza, args=("guwnozer13",), use_container_width=True)
    st.button("🏆 zwycięzca ultraligi", on_click=ustaw_gracza, args=("sfdasrw",), use_container_width=True)

# Główna część aplikacji
if odpal:
    if not nick_input:
        st.error("Wprowadź nickname gracza!")
    else:
        headers = get_headers()
        
        with st.spinner(f'Szukam gracza {nick_input}...'):
            player_info = get_player_info(nick_input, headers)
            
        if not player_info:
            st.error("ni mo albo api albo chlopa")
        else:
            p_id = player_info["player_id"]
            
            # --- SEKCJA NAGŁÓWKA Z AVATAREM I ELO ---
            with st.spinner('obczajanie czy ziomo ma ogar... (liczę ELO)'):
                t_wins, t_losses, t_elo_change = get_todays_wl(p_id, headers)
            
            st.markdown("---")
            col_avatar, col_elo, col_wl, col_empty = st.columns([1, 2, 2, 2])
            
            with col_avatar:
                if player_info["avatar"]:
                    st.image(player_info["avatar"], width=100)
                else:
                    st.write("👤 Brak avatara")
                    
            with col_elo:
                if str(player_info['elo']).isdigit():
                    curr_elo = int(player_info['elo'])
                    yest_elo = curr_elo - t_elo_change
                    znak = "+" if t_elo_change >= 0 else ""
                    
                    st.metric(label="🏆 Aktualne ELO (CS2)", value=curr_elo, delta=f"{t_elo_change} od wczoraj")
                    st.caption(f"Kalkulacja: **{yest_elo}** (wczoraj) {znak}{t_elo_change} (dziś) = **{curr_elo}**")
                else:
                    st.metric(label="🏆 Aktualne ELO (CS2)", value=player_info['elo'])
                
            with col_wl:
                st.metric(label="📅 Dzisiejszy Bilans (W/L)", value=f"{t_wins}W - {t_losses}L")
                
            st.markdown("---")

            # --- POBIERANIE MECZÓW ---
            with st.spinner('Pobieram listę meczów do analizy...'):
                if zakres == "Ostatnie 10 meczy":
                    matches = get_match_history(p_id, 10, headers)
                elif zakres == "Ostatnie 30 meczy":
                    matches = get_match_history(p_id, 30, headers)
                else:
                    midnight = datetime.combine(datetime.today(), datetime.min.time()).timestamp()
                    all_matches = get_match_history(p_id, 50, headers)
                    matches = [m for m in all_matches if m.get("finished_at", 0) >= midnight]

            if not matches:
                st.warning("Brak meczów w wybranym zakresie.")
            else:
                st.info(f"Znaleziono {len(matches)} meczów do analizy")
                
                # Uruchomienie analizy
                wyniki = analyze_data(matches, p_id, headers)
                
                if not wyniki:
                    st.error("Nie udało się pobrać statystyk dla tych meczów.")
                else:
                    st.success(f"Analiza zakończona! Przeanalizowano {wyniki['valid_matches']} meczów.")
                    
                    # --- RYSOWANIE STATYSTYK ---
                    st.markdown("### 📈 Średnie Statystyki")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("K/D Ratio", f"{wyniki['kd']:.2f}")
                    col2.metric("ADR", f"{wyniki['adr']:.1f}")
                    col3.metric("K/R Ratio", f"{wyniki['kr']:.2f}")
                    col4.metric("HS %", f"{wyniki['hs_percent']:.1f}%")

                    col5, col6, col7 = st.columns(3)
                    col5.metric("Śr. Zabójstwa", f"{wyniki['avg_kills']:.1f}")
                    col6.metric("Śr. Śmierci", f"{wyniki['avg_deaths']:.1f}")
                    col7.metric("Śr. Asysty", f"{wyniki['avg_assists']:.1f}")
                    
                    st.divider()
                    
                    # --- RYSOWANIE KATEGORII Z WYKRESAMI ---
                    cat = wyniki['categories']
                    
                    col_win, col_loss = st.columns(2)
                    
                    with col_win:
                        st.markdown("#### ✅ Tinki Winki")
                        st.success(f"🟢 carry ostre (ADR > 95): **{cat['win_carried']}**")
                        st.info(f"🟡 średniawa (ADR 75-95): **{cat['win_avg']}**")
                        st.warning(f"🔴 zagrane jak pies (ADR < 75): **{cat['win_carried_by']}**")
                        
                        # Wykres Win
                        win_values = [cat['win_carried'], cat['win_avg'], cat['win_carried_by']]
                        if sum(win_values) > 0:
                            fig_win = px.pie(
                                names=["Carry ostre", "Średniawa", "Zagrane jak pies"],
                                values=win_values,
                                hole=0.5,
                                color_discrete_sequence=["#198754", "#ffc107", "#dc3545"] # Zielony, Żółty, Czerwony
                            )
                            fig_win.update_traces(textinfo='percent+label', textfont_size=14)
                            fig_win.update_layout(margin=dict(t=20, b=20, l=0, r=0), showlegend=False)
                            st.plotly_chart(fig_win, use_container_width=True)
                        
                    with col_loss:
                        st.markdown("#### 🚫 Looski arbuzki")
                        st.success(f"🟢 n00bki w teamie (ADR > 90): **{cat['loss_trolled']}**")
                        st.info(f"🟡 średniawa (ADR 70-90): **{cat['loss_avg']}**")
                        st.error(f"🔴 ja byłem nobkiem (ADR < 70): **{cat['loss_my_fault']}**")
                        
                        # Wykres Loss
                        loss_values = [cat['loss_trolled'], cat['loss_avg'], cat['loss_my_fault']]
                        if sum(loss_values) > 0:
                            fig_loss = px.pie(
                                names=["N00bki w teamie", "Średniawa", "Ja byłem n00bkiem"],
                                values=loss_values,
                                hole=0.5,
                                color_discrete_sequence=["#198754", "#ffc107", "#dc3545"] # Zielony, Żółty, Czerwony
                            )
                            fig_loss.update_traces(textinfo='percent+label', textfont_size=14)
                            fig_loss.update_layout(margin=dict(t=20, b=20, l=0, r=0), showlegend=False)
                            st.plotly_chart(fig_loss, use_container_width=True)

