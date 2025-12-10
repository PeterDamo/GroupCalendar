import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import init_db, add_activity, get_activities, add_user, get_db_connection

# --- Configurazione e Inizializzazione ---
init_db()

# Variabili di Sessione e Stato
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'nickname' not in st.session_state:
    st.session_state.nickname = None

st.set_page_config(layout="wide", page_title="Calendario Condiviso (Max 10)")

# --- Funzioni di Interfaccia ---

def login_ui():
    """Interfaccia per l'accesso (o registrazione nickname)."""
    st.title("🤝 Accedi al Calendario Condiviso")
    st.info("Inserisci il tuo Nickname. Se sei nuovo, verrai registrato (Max 10 utenti totali).")
    
    with st.form("login_form"):
        nickname = st.text_input("Nickname:")
        submitted = st.form_submit_button("Accedi / Registrati")
        
        if submitted and nickname:
            success, result = add_user(nickname)
            
            if success:
                st.session_state.user_id = result # result è l'ID dell'utente
                st.session_state.nickname = nickname
                st.success(f"Accesso riuscito. Benvenuto/Bentornato, **{nickname}**!")
                
                # CORREZIONE APPLICATA: Uso di st.rerun()
                st.rerun() 
            else:
                # Caso di limite utenti raggiunto
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

            # Combina data e ora e formatta per SQLite
            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(end_date, end_time)

            if start_dt >= end_dt:
                st.sidebar.error("La data/ora di inizio deve essere precedente a quella di fine.")
                return
            
            add_activity(title, description, start_dt.strftime('%Y-%m-%d %H:%M:%S'), 
                         end_dt.strftime('%Y-%m-%d %H:%M:%S'), st.session_state.user_id)
            st.sidebar.success("Attività aggiunta con successo!")
            st.rerun() # Ricarica per aggiornare il calendario

def show_calendar_view(df):
    """Visualizza il calendario principale usando un Gantt Chart Plotly."""
    st.subheader("🗓️ Calendario Condiviso")
    
    # Rinominazione colonne per la visualizzazione
    df.rename(columns={'nickname': 'Creatore', 'title': 'Attività'}, inplace=True)
    
    # 1. Tabella dettagliata
    st.dataframe(df[['Attività', 'start_time', 'end_time', 'Creatore', 'description']], 
                 use_container_width=True,
                 column_config={
                     "start_time": st.column_config.DatetimeColumn("Inizio", format="YYYY/MM/DD HH:mm"),
                     "end_time": st.column_config.DatetimeColumn("Fine", format="YYYY/MM/DD HH:mm"),
                     "description": st.column_config.TextColumn("Descrizione", width="small")
                 },
                 hide_index=True)
    
    # 2. Vista cronologica (Gantt Chart)
    # Calcola la durata in ore per i tooltip
    df['Durata (ore)'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600
    
    fig = px.timeline(df, x_start="start_time", x_end="end_time", y="Attività", 
                      color="Creatore", 
                      title="Vista Cronologica (Gantt Chart)",
                      hover_data=['description', 'Durata (ore)'])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
    

def show_analytics(df):
    """Mostra le analisi mensili e per utente."""
    st.header("📊 Analisi e Report")
    
    # Preparazione dei dati per l'analisi
    df['Mese'] = df['start_time'].dt.to_period('M').astype(str)
    
    if df['Mese'].empty:
        st.warning("Nessun dato temporale per l'analisi.")
        return

    # Selezione del mese
    available_months = sorted(df['Mese'].unique(), reverse=True)
    selected_month = st.selectbox("Seleziona Mese per l'Analisi", available_months)

    df_month = df[df['Mese'] == selected_month]

    col_stats, col_charts = st.columns([1, 2])

    with col_stats:
        st.subheader("Statistiche Mensili")
        total_activities = len(df_month)
        total_duration_hours = df_month['Durata (ore)'].sum()
        
        st.metric("Attività Totali nel Mese", total_activities)
        st.metric("Ore Totali Impegnate", f"{total_duration_hours:,.2f} ore")

    with col_charts:
        st.subheader("Analisi per Utente")
        
        # 1. Conteggio Attività per utente
        activity_counts = df_month.groupby('Creatore')['Attività'].count().reset_index()
        activity_counts.columns = ['Creatore', 'Conteggio Attività']
        
        fig_count = px.bar(activity_counts, x='Creatore', y='Conteggio Attività', 
                           title=f'Numero di Attività create per Utente ({selected_month})',
                           color='Creatore')
        st.plotly_chart(fig_count, use_container_width=True)
        

        # 2. Distribuzione del tempo totale
        duration_per_user = df_month.groupby('Creatore')['Durata (ore)'].sum().reset_index()
        duration_per_user.columns = ['Creatore', 'Ore Totali']

        fig_time = px.pie(duration_per_user, names='Creatore', values='Ore Totali',
                          title=f'Distribuzione del Tempo Impegnato per Utente ({selected_month})')
        st.plotly_chart(fig_time, use_container_width=True)
        

# --- Logica Principale ---

if st.session_state.user_id is None:
    login_ui()
else:
    # L'utente è loggato
    st.sidebar.markdown(f"**Utente Attivo:** {st.session_state.nickname}")
    st.sidebar.markdown("---")

    # 1. Recupera i dati
    activities_data = get_activities()
    
    if not activities_data:
        df_activities = pd.DataFrame(columns=['id', 'title', 'description', 'start_time', 'end_time', 'creator_id', 'nickname'])
    else:
        df_activities = pd.DataFrame(activities_data)
        # Converte le colonne di data/ora in formato datetime (necessario per Plotly e analisi)
        df_activities['start_time'] = pd.to_datetime(df_activities['start_time'])
        df_activities['end_time'] = pd.to_datetime(df_activities['end_time'])
    
    # 2. Layout a Tab
    tab1, tab2 = st.tabs(["Calendario e Inserimento", "Analisi Dati"])
    
    with tab1:
        st.markdown(f"## **Benvenuto, {st.session_state.nickname}!**")
        st.info("Solo il creatore può modificare/eliminare la propria attività. Tutti possono vedere.")
        
        col_main, col_sidebar = st.columns([4, 1])
        
        with col_sidebar:
            add_activity_ui() # Form di aggiunta attività
        
        with col_main:
            if not df_activities.empty:
                show_calendar_view(df_activities)
            else:
                 st.info("Nessuna attività da visualizzare nel calendario.")
        
    with tab2:
        if not df_activities.empty:
            show_analytics(df_activities)
        else:
            st.warning("Nessun dato da analizzare. Aggiungi delle attività al calendario.")

    # Pulsante Logout
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.nickname = None
        # CORREZIONE APPLICATA: Uso di st.rerun()
        st.rerun()
