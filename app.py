import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import init_db, add_activity, get_activities, add_user, get_users, get_db_connection

# Inizializza il DB all'avvio dell'app
init_db()

# --- Variabili di Sessione e Stato ---
# Usiamo st.session_state per gestire l'utente loggato
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'nickname' not in st.session_state:
    st.session_state.nickname = None

st.set_page_config(layout="wide", page_title="Calendario Condiviso (Max 10)")

# --- Funzioni di Interfaccia ---

def login_ui():
    """Interfaccia per l'accesso (o registrazione nickname)."""
    st.subheader("Accedi al Calendario")
    
    with st.form("login_form"):
        nickname = st.text_input("Inserisci il tuo Nickname (Max 10 utenti per calendario)")
        submitted = st.form_submit_button("Accedi / Registrati")
        
        if submitted and nickname:
            success, result = add_user(nickname)
            if success:
                st.session_state.user_id = result # result è l'ID dell'utente
                st.session_state.nickname = nickname
                st.success(f"Benvenuto, {nickname}! Sei stato aggiunto al calendario.")
              st.rerun()
            elif "Nickname già in uso" in result:
                # Se l'utente esiste già, lo recuperiamo
                conn = get_db_connection()
                user_data = conn.execute("SELECT id FROM users WHERE nickname = ?", (nickname,)).fetchone()
                conn.close()
                if user_data:
                    st.session_state.user_id = user_data[0]
                    st.session_state.nickname = nickname
                    st.success(f"Bentornato, {nickname}!")
                    st.experimental_rerun()
                else:
                    st.error("Errore di accesso. Riprova.")
            else:
                st.error(result)

def add_activity_ui():
    """Interfaccia per l'aggiunta di una nuova attività."""
    st.sidebar.subheader(f"Aggiungi Attività ({st.session_state.nickname})")
    
    with st.sidebar.form("activity_form"):
        title = st.text_input("Titolo Attività *")
        description = st.text_area("Descrizione")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Data Inizio *", datetime.now().date())
            start_time = st.time_input("Ora Inizio *", datetime.now().time())
        with col2:
            end_date = st.date_input("Data Fine *", datetime.now().date())
            end_time = st.time_input("Ora Fine *", datetime.now().time())
            
        submitted = st.form_submit_button("Salva Attività")
        
        if submitted:
            if not title:
                st.sidebar.error("Il titolo è obbligatorio.")
                return

            # Combina data e ora
            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(end_date, end_time)

            if start_dt >= end_dt:
                st.sidebar.error("La data/ora di inizio deve essere precedente a quella di fine.")
                return
            
            add_activity(title, description, start_dt, end_dt, st.session_state.user_id)
            st.sidebar.success("Attività aggiunta con successo!")

def show_calendar_view(df):
    """Visualizza il calendario principale."""
    st.subheader("🗓️ Calendario Condiviso")
    
    # Aggiungi colonna Autore per una visualizzazione più chiara
    df.rename(columns={'nickname': 'Creatore', 'title': 'Attività'}, inplace=True)
    
    # Visualizzazione tabellare (può essere sostituita da un widget calendario più complesso)
    st.dataframe(df[['Attività', 'start_time', 'end_time', 'Creatore', 'description']], 
                 use_container_width=True,
                 column_config={
                     "start_time": st.column_config.DatetimeColumn("Inizio", format="YYYY/MM/DD HH:mm"),
                     "end_time": st.column_config.DatetimeColumn("Fine", format="YYYY/MM/DD HH:mm"),
                     "description": st.column_config.TextColumn("Descrizione", width="small")
                 })
    
    # NOTA: Per un vero calendario grafico interattivo, si userebbe una libreria JS integrata.
    # Ad esempio, è possibile usare Plotly per visualizzare un Gantt Chart delle attività.
    df['Durata (ore)'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600
    fig = px.timeline(df, x_start="start_time", x_end="end_time", y="Attività", 
                      color="Creatore", 
                      title="Vista Cronologica delle Attività",
                      hover_data=['description', 'Durata (ore)'])
    fig.update_yaxes(autorange="reversed") # Rende la visualizzazione più leggibile
    st.plotly_chart(fig, use_container_width=True)
    


def show_analytics(df):
    """Mostra le analisi mensili e per utente."""
    st.header("📊 Analisi e Report")
    
    # 1. Preparazione dei dati per l'analisi
    df['Mese'] = df['start_time'].dt.to_period('M').astype(str)
    
    # 2. Selezione del mese
    available_months = sorted(df['Mese'].unique(), reverse=True)
    selected_month = st.selectbox("Seleziona Mese per l'Analisi", available_months)

    df_month = df[df['Mese'] == selected_month]

    col_stats, col_charts = st.columns([1, 2])

    with col_stats:
        st.subheader("Statistiche Mensili")
        total_activities = len(df_month)
        # La durata totale in ore
        total_duration_hours = df_month['Durata (ore)'].sum()
        
        st.metric("Attività Totali nel Mese", total_activities)
        st.metric("Ore Totali Impegnate", f"{total_duration_hours:,.2f} ore")

    with col_charts:
        st.subheader("Analisi per Utente")
        
        # Analisi del numero di attività per utente
        activity_counts = df_month.groupby('Creatore')['Attività'].count().reset_index()
        activity_counts.columns = ['Creatore', 'Conteggio Attività']
        
        fig_count = px.bar(activity_counts, x='Creatore', y='Conteggio Attività', 
                           title=f'Numero di Attività create per Utente ({selected_month})',
                           color='Creatore')
        st.plotly_chart(fig_count, use_container_width=True)
        

        # Analisi del tempo totale impegnato per utente
        duration_per_user = df_month.groupby('Creatore')['Durata (ore)'].sum().reset_index()
        duration_per_user.columns = ['Creatore', 'Ore Totali']

        fig_time = px.pie(duration_per_user, names='Creatore', values='Ore Totali',
                          title=f'Distribuzione del Tempo Impegnato per Utente ({selected_month})')
        st.plotly_chart(fig_time, use_container_width=True)

# --- Logica Principale ---

if st.session_state.user_id is None:
    login_ui()
else:
    # L'utente è loggato. Mostra l'app completa
    
    # 1. Recupera i dati
    activities_data = get_activities()
    if not activities_data:
        st.warning("Il calendario è vuoto. Inserisci la prima attività!")
        df_activities = pd.DataFrame(columns=['id', 'title', 'description', 'start_time', 'end_time', 'creator_id', 'nickname'])
    else:
        df_activities = pd.DataFrame(activities_data, columns=['id', 'title', 'description', 'start_time', 'end_time', 'creator_id', 'nickname'])
        # Converte le colonne di data/ora in formato datetime
        df_activities['start_time'] = pd.to_datetime(df_activities['start_time'])
        df_activities['end_time'] = pd.to_datetime(df_activities['end_time'])
    
    # 2. Layout a Tab
    tab1, tab2 = st.tabs(["Calendario e Inserimento", "Analisi Dati"])
    
    with tab1:
        st.markdown(f"## **Benvenuto, {st.session_state.nickname}!**")
        st.info(f"Link di Condivisione (Fittizio): `https://tuoapp.io/calendario_1234`")
        
        col_main, col_sidebar = st.columns([4, 1])
        
        with col_sidebar:
            add_activity_ui() # Form di aggiunta attività in sidebar
        
        with col_main:
            if not df_activities.empty:
                show_calendar_view(df_activities)
            else:
                 st.info("Nessuna attività da visualizzare nel calendario.")
        
    with tab2:
        if not df_activities.empty:
            show_analytics(df_activities)
        else:
            st.warning("Nessun dato da analizzare. Aggiungi delle attività.")

    # Pulsante Logout (opzionale)
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.nickname = None
        st.experimental_rerun()
