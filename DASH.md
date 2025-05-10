# Dashboard di Telemetria con Flask e Dash

## Panoramica

Questo documento descrive un'applicazione web per la visualizzazione di dati di telemetria utilizzando Flask come server web e Dash per creare un'interfaccia grafica interattiva. L'applicazione legge dati da un file CSV locale (`~/telemetria.csv`) che viene aggiornato ogni minuto con nuove misurazioni.

## Formato dei Dati di Telemetria

Il file CSV di telemetria contiene i seguenti campi:
- `timestamp`: Data e ora della misurazione (formato ISO)
- `pressure`: Pressione del sistema
- `pumpRunning`: Stato della pompa (True/False)
- `outputValveOpen`: Stato della valvola di uscita (True/False)
- `temperature`: Temperatura in gradi Celsius
- `humidity`: Umidità relativa
- `env_pressure`: Pressione ambientale

Esempio:
```
timestamp,pressure,pumpRunning,outputValveOpen,temperature,humidity,env_pressure
2025-05-09T15:55:17.260934,4.756569,False,False,21.99,48.62207,992.7394
2025-05-09T16:00:18.003072,4.391031,False,False,22.07,48.33887,992.7709
```

I dati principali da visualizzare sono:
- pressure
- temperature
- humidity
- env_pressure

## Struttura del Progetto

```
dashboard-flask-dash/
├── app.py                 # File principale dell'applicazione
├── requirements.txt       # Dipendenze Python
└── assets/                # Directory per i file statici
    └── style.css          # (opzionale) Stili personalizzati
```

## Funzionalità dell'Applicazione

1. **Lettura Dinamica dei Dati**
   - L'applicazione legge il file `~/telemetria.csv` ogni minuto
   - Gestisce gli errori di lettura del file restituendo un DataFrame vuoto
   - Non è necessario riavviare l'applicazione quando il file viene aggiornato

2. **Interfaccia Utente**
   - Menu a tendina per selezionare quale sensore visualizzare
   - Grafico interattivo che mostra i valori del sensore nel tempo
   - Aggiornamento automatico ogni 60 secondi

3. **Visualizzazione dei Dati**
   - Grafico a linee per visualizzare l'andamento temporale delle misurazioni
   - Etichette personalizzate per assi X e Y
   - Transizioni animate durante gli aggiornamenti

## Componenti Principali del Codice

### Server Flask
```python
server = flask.Flask(__name__)

@server.route('/')
def index():
    return flask.redirect('/dash/')
```
- Inizializza un'applicazione Flask
- Redireziona la route principale all'applicazione Dash

### Applicazione Dash
```python
app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash/',
    external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css']
)
```
- Configura Dash per usare il server Flask
- Utilizza Bootstrap per lo styling tramite CDN

### Caricamento Dati
```python
def load_data():
    csv_path = os.path.expanduser('~/telemetria.csv')
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Errore caricamento CSV: {e}")
        df = pd.DataFrame()
    return df
```
- Legge il file CSV dalla home directory dell'utente
- Gestisce eventuali errori di lettura

### Layout dell'Interfaccia
```python
app.layout = html.Div(className='container p-4', children=[
    html.H1("Dashboard Telemetria", className='text-center mb-4'),
    dcc.Dropdown(
        id='sensor-dropdown',
        placeholder='Seleziona sensore...',
        style={'width': '50%', 'margin': 'auto'}
    ),
    dcc.Graph(id='telemetry-graph'),
    dcc.Interval(id='interval-update', interval=60*1000, n_intervals=0)
])
```
- Definisce il layout responsivo con componenti Dash
- Configura un intervallo di aggiornamento di 60 secondi

### Callback per il Menu a Tendina
```python
@callback(
    Output('sensor-dropdown', 'options'),
    Input('interval-update', 'n_intervals')
)
def update_dropdown(n):
    df = load_data()
    if df.empty or 'sensor' not in df.columns:
        return []
    sensors = sorted(df['sensor'].unique())
    return [{'label': s, 'value': s} for s in sensors]
```
- Popola il menu a tendina con i sensori disponibili
- Si aggiorna automaticamente ad ogni intervallo

### Callback per il Grafico
```python
@callback(
    Output('telemetry-graph', 'figure'),
    Input('sensor-dropdown', 'value'),
    Input('interval-update', 'n_intervals')
)
def update_graph(selected_sensor, n):
    df = load_data()
    if df.empty or selected_sensor is None or selected_sensor not in df['sensor'].unique():
        return px.line(title="Nessun dato disponibile")
    # Filtro per il sensore selezionato
    dff = df[df['sensor'] == selected_sensor]
    # Converto timestamp se esiste
    if 'timestamp' in dff.columns:
        dff['timestamp'] = pd.to_datetime(dff['timestamp'])
        x_field = 'timestamp'
    else:
        dff = dff.reset_index()
        x_field = 'index'
    # Costruisco il grafico
    fig = px.line(
        dff,
        x=x_field,
        y='value',
        title=f"Valori Telemetria: {selected_sensor}",
        labels={'value': 'Misura', x_field: 'Tempo'}
    )
    fig.update_layout(transition_duration=500)
    return fig
```
- Aggiorna il grafico in base al sensore selezionato
- Converte i timestamp in oggetti datetime
- Configura le etichette e le transizioni animate

## Configurazione e Avvio

### Requirements
Le dipendenze Python necessarie sono:
```
Flask>=2.0
dash>=2.0
pandas
plotly
dash-bootstrap-components
```

### Installazione
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Avvio dell'Applicazione
```bash
python app.py
```

### Accesso
L'applicazione sarà accessibile all'indirizzo `http://<IP-del-Pi>:8050/dash/`

## Adattamento per il Formato Dati Reale

Poiché il formato CSV fornito non contiene una colonna `sensor` ma piuttosto colonne separate per ogni tipo di sensore (`pressure`, `temperature`, ecc.), sarà necessario modificare il codice per:

1. Trasformare i dati dal formato "wide" (colonne multiple) al formato "long" (colonna sensore + colonna valore)
2. Popolare il dropdown con i nomi delle colonne da visualizzare (`pressure`, `temperature`, `humidity`, `env_pressure`)

Questo può essere fatto aggiungendo una funzione di pre-elaborazione che ristruttura i dati prima di visualizzarli.

## Conclusione

Questa applicazione fornisce un modo semplice ma efficace per monitorare i dati di telemetria in tempo reale, con aggiornamenti automatici e un'interfaccia utente intuitiva. È facilmente estensibile per visualizzare diversi tipi di sensori e può essere ulteriormente personalizzata con stili CSS aggiuntivi se necessario.
